from pydantic import BaseModel
from app.shared.enums import WebsiteStatus

from datetime import datetime

class DashboardSummaryResponse(BaseModel):
    total_websites: int
    active_websites: int
    inactive_websites: int
    websites_up: int
    websites_down: int
    websites_unknown: int
    open_incidents: int
    average_response_time_ms: float

class DashboardWebsiteResponse(BaseModel):
    id: str
    name: str
    url: str
    status: WebsiteStatus
    response_time_ms: int | None
    last_checked_at: datetime | None
    is_active: bool

class DashboardIncidentResponse(BaseModel):
    id: str
    website_id: str
    website_name: str
    started_at: datetime
    resolved_at: datetime | None
    duration_seconds: int | None

class DashboardActivityResponse(BaseModel):
    website_name: str
    status: WebsiteStatus
    status_code: int | None
    response_time_ms: int | None
    checked_at: datetime