import time
import httpx
from app.core.logger import get_logger
from app.shared.enums import WebsiteStatus
from app.modules.monitor.schemas import HealthCheckResponse
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.modules.monitor_results.service import MonitorResultService
from app.modules.incident.service import IncidentService
from app.shared.models.HTTP_monitor import WebsiteModel
from datetime import datetime, timezone
from app.modules.monitor_state.enums import MonitorTransition
from app.modules.monitor_state.service import MonitorStateService

logger = get_logger(__name__)

class MonitorService:
    def __init__(self, website_repository: HTTP_monitorRepository, incident_service: IncidentService, monitor_result_service: MonitorResultService, monitor_state_service: MonitorStateService):
        self.website_repository = website_repository
        self.incident_service = incident_service
        self.monitor_result_service = monitor_result_service
        self.monitor_state_service = monitor_state_service

        self.client = httpx.AsyncClient(follow_redirects=True)

    async def check_website(self, website: WebsiteModel) -> HealthCheckResponse:
        start = time.perf_counter()

        status = WebsiteStatus.DOWN
        success = False
        status_code = None
        response_time_ms = None
        try:
            response = await self.client.get(website.url, timeout=website.timeout)

            elapsed = int((time.perf_counter() - start) * 1000)
            status_code = response.status_code
            response_time_ms = elapsed
            success = response.status_code == website.expected_status_code
            status = WebsiteStatus.UP if success else WebsiteStatus.DOWN

            if success:
                logger.info("Website '%s' is UP (%d ms, HTTP %d).", website.name, elapsed, response.status_code)
            else:
                logger.warning("Website '%s' is DOWN (expected %d, got %d).", website.name, website.expected_status_code, response.status_code)

        except httpx.TimeoutException:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check timed out for '%s'.", website.name)

        except httpx.HTTPError as exc:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check failed for '%s' : %s", website.name, exc)

        except Exception:
            logger.exception("Unexpected error while checking '%s'.", website.name)

        return HealthCheckResponse(
            url=website.url,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            success=success,
        )

    async def close(self):
        await self.client.aclose()

    async def check_and_update(self, website: WebsiteModel) -> None:

        result = await self.check_website(website)
        checked_at = datetime.now(timezone.utc)

        await self.monitor_result_service.record_result(
            website_id=website.id,
            status=result.status,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            success=result.success,
        )

        state_result = await self.monitor_state_service.process_result(
            website_id=website.id,
            success=result.success,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            checked_at=checked_at,
        )

        await self.website_repository.update_monitoring_result(
            website_id=website.id,
            status=state_result.current_status,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            checked_at=checked_at,
        )

        logger.info(
            "Health Check | Website='%s' | Status=%s | HTTP=%s | Response=%s ms | Success=%d | Failure=%d",
            website.name,
            state_result.current_status.value,
            result.status_code,
            result.response_time_ms,
            state_result.state.consecutive_successes,
            state_result.state.consecutive_failures,
        )
        if state_result.transition == MonitorTransition.DOWN:

            active = await self.incident_service.get_active_incident(
                website.id
            )

            if active is None:
                reason = (
                    f"HTTP {result.status_code}"
                    if result.status_code is not None
                    else "Timeout / Network Error"
                )

                await self.incident_service.open_incident(
                    website.id,
                    reason,
                )

                logger.warning(
                    "Incident opened for '%s'.",
                    website.name,
                )

        elif state_result.transition == MonitorTransition.UP:

            await self.incident_service.resolve_incident(
                website.id,
            )

            logger.info(
                "Incident resolved for '%s'.",
                website.name,
            )