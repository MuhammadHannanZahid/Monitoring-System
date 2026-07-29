from datetime import datetime
from pydantic import BaseModel
from app.shared.enums import WebsiteStatus

class MonitorResultModel(BaseModel):
    id: str | None = None
    website_id: str
    status: WebsiteStatus
    status_code: int | None
    response_time_ms: int | None
    success: bool
    checked_at: datetime