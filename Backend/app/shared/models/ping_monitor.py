from app.shared.models.base_monitor import BaseMonitorModel
from app.shared.enums import MonitorType

class PingMonitorModel(BaseMonitorModel):
    host: str
    monitor_type: MonitorType = MonitorType.PING
    expected_response_time_ms: int | None = None