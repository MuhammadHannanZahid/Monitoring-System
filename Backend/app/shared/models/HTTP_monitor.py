from pydantic import ConfigDict
from app.shared.models.base_monitor import BaseMonitorModel
from app.shared.enums import MonitorType

class HTTPMonitorModel(BaseMonitorModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    monitor_type: MonitorType = MonitorType.HTTP
    url: str
    expected_status_code: int
    created_by: str | None = None
    failure_count: int = 0
    success_count: int = 0
    expected_response_time_ms: int | None = None