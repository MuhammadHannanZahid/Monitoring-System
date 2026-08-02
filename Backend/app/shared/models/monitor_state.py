from datetime import datetime
from pydantic import BaseModel
from app.shared.enums import HTTP_monitorStatus

class MonitorStateModel(BaseModel):
    monitor_id: str
    status: HTTP_monitorStatus = HTTP_monitorStatus.UNKNOWN
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_checked_at: datetime | None = None
    last_status_code: int | None = None
    last_response_time_ms: int | None = None