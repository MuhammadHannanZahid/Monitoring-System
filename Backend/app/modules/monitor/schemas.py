from pydantic import BaseModel
from app.shared.enums import MonitorStatus, PerformanceStatus

class HealthCheckResponse(BaseModel):
    url: str
    status: MonitorStatus
    status_code: int | None
    response_time_ms: int | None
    success: bool
    is_slow: bool = False
    performance_status: PerformanceStatus = PerformanceStatus.UNKNOWN