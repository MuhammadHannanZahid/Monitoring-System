from app.modules.HTTP_monitor.schemas import HTTP_monitorResponse
from app.shared.models.HTTP_monitor import HTTPMonitorModel

class HTTP_monitorMapper:
    @staticmethod
    def to_response(http_monitor: HTTPMonitorModel) -> HTTP_monitorResponse:
        return HTTP_monitorResponse(
            id=http_monitor.id,
            name=http_monitor.name,
            url=http_monitor.url,
            check_interval=http_monitor.check_interval,
            timeout=http_monitor.timeout,
            expected_status_code=http_monitor.expected_status_code,
            is_active=http_monitor.is_active,
            created_at=http_monitor.created_at,
            updated_at=http_monitor.updated_at,
            last_checked_at=http_monitor.last_checked_at,
            last_status_code=http_monitor.last_status_code,
            last_response_time_ms=http_monitor.last_response_time_ms,
            status=http_monitor.status
        )

    @staticmethod
    def to_response_list(http_monitors: list[HTTPMonitorModel]) -> list[HTTP_monitorResponse]:
        return [
            HTTP_monitorMapper.to_response(http_monitor)
            for http_monitor in http_monitors
        ]