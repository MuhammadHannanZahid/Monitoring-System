from pydantic import BaseModel
from app.shared.enums import WebsiteStatus

class DashboardSummaryResponse(BaseModel):
    total_websites: int
    active_websites: int
    inactive_websites: int
    websites_up: int
    websites_down: int
    websites_unknown: int
    open_incidents: int
    average_response_time_ms: float