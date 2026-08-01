from app.modules.HTTP_monitor.schemas import HTTP_monitorResponse
from app.shared.models.HTTP_monitor import HTTP_monitorModel

class HTTP_monitorMapper:
    @staticmethod
    def to_response(HTTP_monitor: HTTP_monitorModel) -> HTTP_monitorResponse:
        return HTTP_monitorResponse(
            id=HTTP_monitor.id,
            name=HTTP_monitor.name,
            url=HTTP_monitor.url,
            check_interval=HTTP_monitor.check_interval,
            timeout=HTTP_monitor.timeout,
            expected_status_code=HTTP_monitor.expected_status_code,
            is_active=HTTP_monitor.is_active,
            created_at=HTTP_monitor.created_at,
            updated_at=HTTP_monitor.updated_at,
            last_checked_at=HTTP_monitor.last_checked_at,
            last_status_code=HTTP_monitor.last_status_code,
            last_response_time_ms=HTTP_monitor.last_response_time_ms,
            status=HTTP_monitor.status
        )

    @staticmethod
    def to_response_list(HTTP_monitors: list[HTTP_monitorModel]) -> list[HTTP_monitorResponse]:
        return [
            HTTP_monitorMapper.to_response(HTTP_monitor)
            for HTTP_monitor in HTTP_monitors
        ]