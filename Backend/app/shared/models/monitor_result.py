from datetime import datetime
from pydantic import BaseModel
from app.shared.enums import HTTP_monitorStatus

class MonitorResultModel(BaseModel):
    id: str | None = None
    monitor_id: str
    status: HTTP_monitorStatus
    status_code: int | None
    response_time_ms: int | None
    success: bool
    checked_at: datetime