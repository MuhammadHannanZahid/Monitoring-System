from pydantic import BaseModel
from app.shared.enums import HTTP_monitorStatus

class HealthCheckResponse(BaseModel):
    url: str
    status: HTTP_monitorStatus
    status_code: int | None
    response_time_ms: int | None
    success: bool