import time
import httpx
from app.core.logger import get_logger
from app.shared.enums import HTTP_monitorStatus
from app.modules.monitor.schemas import HealthCheckResponse
from app.modules.monitor_results.service import MonitorResultService
from app.modules.incident.service import IncidentService
from datetime import datetime, timezone
from app.modules.monitor_state.enums import MonitorTransition
from app.modules.monitor_state.service import MonitorStateService
from app.modules.monitor.checkers.checker_factory import CheckerFactory
from app.shared.models.base_monitor import BaseMonitorModel

logger = get_logger(__name__)

class MonitorService:
    def __init__(self, repository_factory: MonitorRepositoryFactory, incident_service: IncidentService, monitor_result_service: MonitorResultService, monitor_state_service: MonitorStateService, checker_factory: CheckerFactory):
        self.repository_factory = repository_factory
        self.incident_service = incident_service
        self.monitor_result_service = monitor_result_service
        self.monitor_state_service = monitor_state_service
        self.checker_factory = checker_factory

    async def check_and_update(self, monitor: BaseMonitorModel) -> None:

        checker = self.checker_factory.get_checker(
            monitor.monitor_type
        )

        result = await checker.check(monitor)
        checked_at = datetime.now(timezone.utc)

        await self.monitor_result_service.record_result(
            monitor_id=monitor.id,
            monitor_type=monitor.monitor_type,
            status=result.status,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            success=result.success,
        )

        state_result = await self.monitor_state_service.process_result(
            monitor_id=monitor.id,
            monitor_type=monitor.monitor_type,
            success=result.success,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            checked_at=checked_at,
        )

        repository = self.repository_factory.get_repository(monitor.monitor_type)
        await repository.update_monitoring_result(
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
                monitor.id,
                monitor.monitor_type,
            )

            if active is None:
                reason = (
                    f"HTTP {result.status_code}"
                    if result.status_code is not None
                    else "Timeout / Network Error"
                )

                await self.incident_service.open_incident(
                    monitor.id,
                    monitor.monitor_type,
                    reason,
                )

                logger.warning(
                    "Incident opened for '%s'.",
                    monitor.name,
                )

        elif state_result.transition == MonitorTransition.UP:

            await self.incident_service.resolve_incident(
                monitor.id,
                monitor.monitor_type,
            )

            logger.info(
                "Incident resolved for '%s'.",
                monitor.name,
            )