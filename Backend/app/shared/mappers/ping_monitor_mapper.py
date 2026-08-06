from app.modules.ping_monitor.schemas import PingMonitorResponse
from app.shared.models.ping_monitor import PingMonitorModel

class PingMonitorMapper:
    @staticmethod
    def to_response(monitor: PingMonitorModel) -> PingMonitorResponse:
        return PingMonitorResponse(
            id=monitor.id,
            name=monitor.name,
            host=monitor.host,
            check_interval=monitor.check_interval,
            timeout=monitor.timeout,
            expected_response_time_ms=monitor.expected_response_time_ms,
            is_active=monitor.is_active,
            created_by=monitor.created_by,
            created_at=monitor.created_at,
            updated_at=monitor.updated_at,
            last_checked_at=monitor.last_checked_at,
            last_status_code=monitor.last_status_code,
            last_response_time_ms=monitor.last_response_time_ms,
            status=monitor.status,
        )

    @staticmethod
    def to_response_list(monitors: list[PingMonitorModel]) -> list[PingMonitorResponse]:
        return [
            PingMonitorMapper.to_response(monitor)
            for monitor in monitors
        ]