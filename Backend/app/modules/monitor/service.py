import time
import httpx
from app.core.logger import get_logger
from app.shared.enums import HTTP_monitorStatus
from app.modules.monitor.schemas import HealthCheckResponse
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.modules.monitor_results.service import MonitorResultService
from app.modules.incident.service import IncidentService
from app.shared.models.HTTP_monitor import HTTP_monitorModel
from datetime import datetime, timezone
from app.modules.monitor_state.enums import MonitorTransition
from app.modules.monitor_state.service import MonitorStateService

logger = get_logger(__name__)

class MonitorService:
    def __init__(self, HTTP_monitor_repository: HTTP_monitorRepository, incident_service: IncidentService, monitor_result_service: MonitorResultService, monitor_state_service: MonitorStateService):
        self.monitor_repository = HTTP_monitor_repository
        self.incident_service = incident_service
        self.monitor_result_service = monitor_result_service
        self.monitor_state_service = monitor_state_service

        self.client = httpx.AsyncClient(follow_redirects=True)

    async def check_monitor(self, HTTP_monitor: HTTP_monitorModel) -> HealthCheckResponse:
        start = time.perf_counter()

        status = HTTP_monitorStatus.DOWN
        success = False
        status_code = None
        response_time_ms = None
        try:
            response = await self.client.get(HTTP_monitor.url, timeout=HTTP_monitor.timeout)

            elapsed = int((time.perf_counter() - start) * 1000)
            status_code = response.status_code
            response_time_ms = elapsed
            success = response.status_code == HTTP_monitor.expected_status_code
            status = HTTP_monitorStatus.UP if success else HTTP_monitorStatus.DOWN

            if success:
                logger.info("Monitor '%s' is UP (%d ms, HTTP %d).", HTTP_monitor.name, elapsed, response.status_code)
            else:
                logger.warning("Monitor '%s' is DOWN (expected %d, got %d).", HTTP_monitor.name, HTTP_monitor.expected_status_code, response.status_code)

        except httpx.TimeoutException:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check timed out for '%s'.", HTTP_monitor.name)

        except httpx.HTTPError as exc:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check failed for '%s' : %s", HTTP_monitor.name, exc)

        except Exception:
            logger.exception("Unexpected error while checking '%s'.", HTTP_monitor.name)

        return HealthCheckResponse(
            url=HTTP_monitor.url,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            success=success,
        )

    async def close(self):
        await self.client.aclose()

    async def check_and_update(self, monitor: HTTP_monitorModel) -> None:

        result = await self.check_monitor(monitor)
        checked_at = datetime.now(timezone.utc)

        await self.monitor_result_service.record_result(
            monitor_id=monitor.id,
            status=result.status,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            success=result.success,
        )

        state_result = await self.monitor_state_service.process_result(
            monitor_id=monitor.id,
            success=result.success,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            checked_at=checked_at,
        )

        await self.monitor_repository.update_monitoring_result(
            monitor_id=monitor.id,
            status=state_result.current_status,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            checked_at=checked_at,
        )

        logger.info(
            "Health Check | monitor='%s' | Status=%s | HTTP=%s | Response=%s ms | Success=%d | Failure=%d",
            monitor.name,
            state_result.current_status.value,
            result.status_code,
            result.response_time_ms,
            state_result.state.consecutive_successes,
            state_result.state.consecutive_failures,
        )
        if state_result.transition == MonitorTransition.DOWN:

            active = await self.incident_service.get_active_incident(
                monitor.id
            )

            if active is None:
                reason = (
                    f"HTTP {result.status_code}"
                    if result.status_code is not None
                    else "Timeout / Network Error"
                )

                await self.incident_service.open_incident(
                    monitor.id,
                    reason,
                )

                logger.warning(
                    "Incident opened for '%s'.",
                    monitor.name,
                )

        elif state_result.transition == MonitorTransition.UP:

            await self.incident_service.resolve_incident(
                monitor.id,
            )

            logger.info(
                "Incident resolved for '%s'.",
                monitor.name,
            )