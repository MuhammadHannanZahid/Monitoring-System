from datetime import datetime
from pydantic import BaseModel
from app.service.mongo_db.shared_models.db_monitoring_controller_model import MonitorStatus

class DashboardSummaryResponse(BaseModel):
    total_monitors: int
    active_monitors: int
    inactive_monitors: int
    monitors_up: int
    monitors_down: int
    monitors_unknown: int
    slow_monitors: int
    open_incidents: int
    average_response_time_ms: float

class DashboardIncidentResponse(BaseModel):
    id: str
    monitor_id: str
    monitor_name: str
    started_at: datetime
    resolved_at: datetime | None
    duration_seconds: int | None

class DashboardActivityResponse(BaseModel):
    monitor_name: str
    status: MonitorStatus
    status_code: int | None
    response_time_ms: int | None
    is_slow: bool
    checked_at: datetime

class ResponseHistoryPoint(BaseModel):
    checked_at: datetime
    response_time_ms: int | None

class ResponseHistoryResponse(BaseModel):
    monitor_id: str
    points: list[ResponseHistoryPoint]

class UptimeResponse(BaseModel):
    monitor_id: str
    uptime_percentage: float
    total_checks: int
    successful_checks: int
    failed_checks: int
    slow_checks: int

class StatusHistoryPoint(BaseModel):
    checked_at: datetime
    status: MonitorStatus

class StatusHistoryResponse(BaseModel):
    monitor_id: str
    history: list[StatusHistoryPoint]