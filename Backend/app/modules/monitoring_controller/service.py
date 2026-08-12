from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from app.core.logger import get_logger
from app.modules.incident_manager.service import IncidentService
from app.modules.monitoring_controller.checkers.checker_factory import CheckerFactory
from app.modules.monitoring_controller.monitor_state.service import MonitorStateService
from app.modules.monitoring_controller.monitor_results.service import MonitorResultService
from app.service.mongo_db.shared_models.models.base_monitor import BaseMonitorModel
from app.service.mongo_db.shared_models.models.heartbeat_monitor import HeartbeatMonitorModel
from app.service.mongo_db.shared_models.models.monitor_state import MonitorTransition
from app.service.mongo_db.shared_models.models.base_monitor import MonitorStatus, MonitorType

if TYPE_CHECKING:
    from app.modules.api_monitor_manager.service import API_monitorService
    from app.modules.http_monitor_manager.service import HTTP_monitorService
    from app.modules.heartbeat_monitor_manager.service import HeartbeatMonitorService
    from app.modules.ping_monitor_manager.service import PingMonitorService

logger = get_logger(__name__)

MonitorModel = BaseMonitorModel | HeartbeatMonitorModel

class MonitorService:
    def __init__(
        self,
        http_monitor_service: HTTP_monitorService,
        api_monitor_service: API_monitorService,
        ping_monitor_service: PingMonitorService,
        heartbeat_monitor_service: HeartbeatMonitorService,
        incident_service: IncidentService,
        monitor_result_service: MonitorResultService,
        monitor_state_service: MonitorStateService,
        checker_factory: CheckerFactory,
    ):
        self.http_monitor_service = http_monitor_service
        self.api_monitor_service = api_monitor_service
        self.ping_monitor_service = ping_monitor_service
        self.heartbeat_monitor_service = heartbeat_monitor_service
        self.incident_service = incident_service
        self.monitor_result_service = monitor_result_service
        self.monitor_state_service = monitor_state_service
        self.checker_factory = checker_factory
        self._monitor_services = {
            MonitorType.HTTP: http_monitor_service,
            MonitorType.API: api_monitor_service,
            MonitorType.PING: ping_monitor_service,
            MonitorType.HEARTBEAT: heartbeat_monitor_service,
        }

    async def list_active_monitors(self):
        return [
            monitor
            for monitor in await self.list_monitors()
            if monitor.is_active
        ]

    async def check_and_update(self, monitor: MonitorModel) -> None:
        try:
            service = self._get_monitor_service(monitor.monitor_type)
            latest_monitor = await service.get_monitor(monitor.id)
            if latest_monitor is None:
                logger.warning("Monitor '%s' no longer exists. Skipping check.", monitor.id)
                return

            if latest_monitor.monitor_type == MonitorType.HEARTBEAT and latest_monitor.last_heartbeat_at is None:
                return

            checker = self.checker_factory.get_checker(monitor.monitor_type)
            result = await checker.check(latest_monitor)
            checked_at = datetime.now(timezone.utc)

            await self.monitor_result_service.record_result(
                monitor_id=monitor.id,
                monitor_type=monitor.monitor_type,
                status=result.status,
                status_code=result.status_code,
                response_time_ms=result.response_time_ms,
                success=result.success,
                is_slow=result.is_slow,
            )

            state_result = await self.monitor_state_service.process_result(
                monitor_id=monitor.id,
                monitor_type=monitor.monitor_type,
                success=result.success,
                status_code=result.status_code,
                response_time_ms=result.response_time_ms,
                checked_at=checked_at,
            )

            await service.update_monitoring_result(
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
        except Exception:
            logger.exception("Failed to process monitor '%s'.", monitor.name)

    async def _handle_incident_transition(self, monitor: MonitorModel, result, state_result) -> None:
        if state_result.transition == MonitorTransition.DOWN:
            active = await self.incident_service.get_active_incident(monitor.id, monitor.monitor_type)
            if active is None:
                reason = self._build_incident_reason(monitor, result)
                await self.incident_service.open_incident(monitor.id, monitor.monitor_type, reason)
                logger.warning("Incident opened for '%s'.", monitor.name)

        elif state_result.transition == MonitorTransition.UP:
            await self.incident_service.resolve_incident(monitor.id, monitor.monitor_type)
            logger.info("Incident resolved for '%s'.", monitor.name)

    def _build_incident_reason(self, monitor: MonitorModel, result) -> str:
        if monitor.monitor_type == MonitorType.HEARTBEAT:
            return "Heartbeat was not received."

        if (
                hasattr(result, "status_code")
                and result.status_code is not None
                and hasattr(monitor, "expected_status_code")
                and monitor.expected_status_code is not None
                and result.status_code != monitor.expected_status_code
        ):
            return (
                f"Expected HTTP {monitor.expected_status_code}, "
                f"got HTTP {result.status_code}."
            )
        if (
                hasattr(result, "response_time_ms")
                and hasattr(monitor, "timeout")
                and result.response_time_ms is not None
                and monitor.timeout is not None
                and result.response_time_ms >= monitor.timeout
        ):
            return "Health check timed out."
        if hasattr(result, "success") and not result.success:
            return "Health check failed."
        return "Monitor is unreachable."

    async def get_monitor(self, monitor_id: str, monitor_type: MonitorType | None = None) -> MonitorModel | None:
        if monitor_type is not None:
            return await self._get_monitor_service(monitor_type).get_monitor(monitor_id)
        for service in self._monitor_services.values():
            monitor = await service.get_monitor(monitor_id)
            if monitor is not None:
                return monitor
        return None

    async def get_monitors_with_lookup(self) -> tuple[list[object], dict[str, object]]:
        monitors = await self.list_monitors()

        return (
            monitors,
            {
                monitor.id: monitor
                for monitor in monitors
            },
        )

    async def list_monitors(self) -> list[MonitorModel]:
        http_monitors = await self.http_monitor_service.list_monitors()
        api_monitors = await self.api_monitor_service.list_monitors()
        ping_monitors = await self.ping_monitor_service.list_monitors()
        heartbeat_monitors = await self.heartbeat_monitor_service.list_monitors()
        return [
            *http_monitors,
            *api_monitors,
            *ping_monitors,
            *heartbeat_monitors,
        ]

    async def process_heartbeat(self, monitor: HeartbeatMonitorModel) -> None:
        checked_at = datetime.now(timezone.utc)
        await self.monitor_result_service.record_result(
            monitor_id=monitor.id,
            monitor_type=monitor.monitor_type,
            status=MonitorStatus.UP,
            status_code=None,
            response_time_ms=None,
            success=True,
            is_slow=False,
        )

        state_result = await self.monitor_state_service.process_result(
            monitor_id=monitor.id,
            monitor_type=monitor.monitor_type,
            success=True,
            status_code=None,
            response_time_ms=None,
            checked_at=checked_at,
        )

        await self.heartbeat_monitor_service.update_monitoring_result(
            monitor_id=monitor.id,
            status=state_result.current_status,
            status_code=None,
            response_time_ms=None,
            checked_at=checked_at,
        )

        logger.info("Heartbeat monitor '%s' is %s; %s", monitor.name, state_result.current_status.value.upper(), self._heartbeat_timing_message(monitor, checked_at))

        await self._handle_incident_transition(
            monitor,
            None,
            state_result,
        )

    def _get_monitor_service(self, monitor_type: MonitorType):
        try:
            return self._monitor_services[monitor_type]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported monitor type: {monitor_type}"
            ) from exc

    @staticmethod
    def _heartbeat_timing_message(monitor: HeartbeatMonitorModel, received_at: datetime) -> str:
        if monitor.last_heartbeat_at is None:
            return (
                "first beat received; next beat expected in "
                f"{monitor.expected_heartbeat_interval} seconds"
            )

        elapsed_seconds = max(
            0.0,
            (received_at - monitor.last_heartbeat_at).total_seconds(),
        )
        difference = monitor.expected_heartbeat_interval - elapsed_seconds

        if difference > 0:
            return (
                f"beat received {difference:.2f} seconds earlier than the "
                f"expected {monitor.expected_heartbeat_interval}-second interval"
            )
        if difference < 0:
            return (
                f"beat received {abs(difference):.2f} seconds later than the "
                f"expected {monitor.expected_heartbeat_interval}-second interval"
            )
        return (
            "beat received exactly at the expected "
            f"{monitor.expected_heartbeat_interval}-second interval"
        )
