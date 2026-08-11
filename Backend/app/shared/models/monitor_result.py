from datetime import datetime
from pydantic import BaseModel
from app.shared.models.base_monitor import MonitorStatus, MonitorType

class MonitorResultModel(BaseModel):
    id: str | None = None
    monitor_id: str
    monitor_type: MonitorType
    status: MonitorStatus
    status_code: int | None = None
    response_time_ms: int | None = None
    success: bool
    is_slow: bool = False
    checked_at: datetime
