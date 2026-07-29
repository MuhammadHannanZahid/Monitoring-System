from pydantic import BaseModel
from app.shared.enums import WebsiteStatus

class HealthCheckResponse(BaseModel):
    url: str
    status: WebsiteStatus
    status_code: int | None
    response_time_ms: int | None
    success: bool