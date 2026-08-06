from pydantic import ConfigDict, Field
from app.shared.models.base_monitor import BaseMonitorModel
from app.shared.enums import MonitorType

class APIMonitorModel(BaseMonitorModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    monitor_type: MonitorType = MonitorType.API
    url: str
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    request_body: dict | None = None
    expected_status_code: int
    expected_json: dict | None = None
    expected_response_time_ms: int | None = None
    expected_headers: dict[str, str] | None = None
    expected_content_type: str | None = None