from pydantic import BaseModel
from app.shared.enums import HTTP_monitorStatus
from datetime import datetime

class DashboardSummaryResponse(BaseModel):
    total_monitors: int
    active_monitors: int
    inactive_monitors: int
    monitors_up: int
    monitors_down: int
    monitors_unknown: int
    open_incidents: int
    average_response_time_ms: float

class DashboardMonitorResponse(BaseModel):
    id: str
    name: str
    url: str
    status: HTTP_monitorStatus | None = None
    response_time_ms: int | None
    status_code: int | None
    uptime_percentage: float | None = None
    incidents: int | None = None
    last_checked_at: datetime | None
    is_active: bool

class DashboardIncidentResponse(BaseModel):
    id: str
    monitor_id: str
    monitor_name: str
    started_at: datetime
    resolved_at: datetime | None
    duration_seconds: int | None

class DashboardActivityResponse(BaseModel):
    monitor_name: str
    status: HTTP_monitorStatus
    status_code: int | None
    response_time_ms: int | None
    checked_at: datetime

class ResponseHistoryPoint(BaseModel):
    checked_at: datetime
    response_time_ms: int

class ResponseHistoryResponse(BaseModel):
    monitor_id: str
    points: list[ResponseHistoryPoint]

class UptimeResponse(BaseModel):
    monitor_id: str
    uptime_percentage: float
    total_checks: int
    successful_checks: int
    failed_checks: int

class StatusHistoryPoint(BaseModel):
    checked_at: datetime
    status: HTTP_monitorStatus

class StatusHistoryResponse(BaseModel):
    monitor_id: str
    history: list[StatusHistoryPoint]