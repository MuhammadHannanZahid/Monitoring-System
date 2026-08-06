from app.shared.models.api_monitor import APIMonitorModel
from app.modules.API_monitor.schemas import ApiMonitorResponse

class API_monitorMapper:
    @staticmethod
    def to_response(API_monitor: APIMonitorModel) -> ApiMonitorResponse:
        return ApiMonitorResponse(
            id=API_monitor.id,
            name=API_monitor.name,
            url=API_monitor.url,
            method=API_monitor.method,
            headers=API_monitor.headers,
            request_body=API_monitor.request_body,
            expected_status_code=API_monitor.expected_status_code,
            expected_json=API_monitor.expected_json,
            check_interval=API_monitor.check_interval,
            timeout=API_monitor.timeout,
            is_active=API_monitor.is_active,
            created_by=API_monitor.created_by,
            created_at=API_monitor.created_at,
            updated_at=API_monitor.updated_at,
            last_checked_at=API_monitor.last_checked_at,
            last_status_code=API_monitor.last_status_code,
            last_response_time_ms=API_monitor.last_response_time_ms,
            status=API_monitor.status,
            expected_response_time_ms=API_monitor.expected_response_time_ms,
            expected_headers=API_monitor.expected_headers,
            expected_content_type=API_monitor.expected_content_type,
        )

    @staticmethod
    def to_response_list(API_monitors: list[APIMonitorModel]) -> list[ApiMonitorResponse]:
        return [
            API_monitorMapper.to_response(API_monitor)
            for API_monitor in API_monitors
        ]