from datetime import datetime, timezone
from app.core.logger import get_logger
from app.modules.incident.service import IncidentService
from app.modules.monitor.checkers.checker_factory import CheckerFactory
from app.modules.monitor.repository_factory import MonitorRepositoryFactory
from app.modules.monitor_state.enums import MonitorTransition
from app.modules.monitor_state.service import MonitorStateService
from app.modules.monitor_results.service import MonitorResultService
from app.shared.models.base_monitor import BaseMonitorModel

logger = get_logger(__name__)

class MonitorService:
    def __init__(self, repository_factory: MonitorRepositoryFactory, incident_service: IncidentService, monitor_result_service: MonitorResultService, monitor_state_service: MonitorStateService, checker_factory: CheckerFactory):
        self.repository_factory = repository_factory
        self.incident_service = incident_service
        self.monitor_result_service = monitor_result_service
        self.monitor_state_service = monitor_state_service
        self.checker_factory = checker_factory

    async def list_active_monitors(self):
        return await self.repository_factory.list_active_monitors()

    async def check_and_update(self, monitor: BaseMonitorModel) -> None:
        checker = self.checker_factory.get_checker(monitor.monitor_type)
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

        await self.repository_factory.update_monitoring_result(
            monitor_type=monitor.monitor_type,
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

        await self._handle_incident_transition(monitor, result, state_result)
        self._log_result(monitor, result, state_result)

    async def _handle_incident_transition(self, monitor: BaseMonitorModel, result, state_result) -> None:
        if state_result.transition == MonitorTransition.DOWN:
            active = await self.incident_service.get_active_incident(monitor.id, monitor.monitor_type)
            if active is None:
                reason = self._build_incident_reason(result)
                await self.incident_service.open_incident(monitor.id, monitor.monitor_type, reason)
                logger.warning("Incident opened for '%s'.", monitor.name)

        elif state_result.transition == MonitorTransition.UP:
            await self.incident_service.resolve_incident(monitor.id, monitor.monitor_type)
            logger.info("Incident resolved for '%s'.", monitor.name)

    def _build_incident_reason(self, result) -> str:
        if result.status_code is not None:
            return f"HTTP {result.status_code}"
        return "Timeout / Network Error"