from datetime import datetime
from pydantic import BaseModel
from app.shared.enums import MonitorStatus, MonitorType

class BaseMonitorModel(BaseModel):
    id: str | None = None
    name: str
    monitor_type: MonitorType
    status: MonitorStatus = MonitorStatus.UNKNOWN
    check_interval: int
    timeout: int
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_checked_at: datetime | None = None
    last_status_code: int | None = None
    last_response_time_ms: int | None = None