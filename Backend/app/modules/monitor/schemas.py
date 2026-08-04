from pydantic import BaseModel
from app.shared.enums import MonitorStatus

class HealthCheckResponse(BaseModel):
    url: str
    status: MonitorStatus
    status_code: int | None
    response_time_ms: int | None
    success: bool