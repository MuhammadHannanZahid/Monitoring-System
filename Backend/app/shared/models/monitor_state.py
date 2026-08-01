from datetime import datetime
from pydantic import BaseModel
from app.shared.enums import WebsiteStatus

class MonitorStateModel(BaseModel):
    website_id: str
    status: WebsiteStatus = WebsiteStatus.UNKNOWN
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_checked_at: datetime | None = None
    last_status_code: int | None = None
    last_response_time_ms: int | None = None