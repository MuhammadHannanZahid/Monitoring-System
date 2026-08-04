from datetime import datetime
from pydantic import BaseModel
from app.shared.enums import MonitorStatus, MonitorType

class MonitorResultModel(BaseModel):
    id: str | None = None
    monitor_id: str
    monitor_type: MonitorType
    status: MonitorStatus
    status_code: int | None = None
    response_time_ms: int | None = None
    success: bool
    checked_at: datetime