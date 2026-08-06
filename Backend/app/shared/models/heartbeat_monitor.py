from datetime import datetime
from pydantic import Field
from app.shared.enums import MonitorStatus, MonitorType
from app.shared.models.base_monitor import BaseMonitorModel

class HeartbeatMonitorModel(BaseMonitorModel):
    monitor_type: MonitorType = MonitorType.HEARTBEAT
    heartbeat_token_hash: str
    check_interval: int
    grace_period: int = 60
    last_heartbeat_at: datetime | None = None
    status: MonitorStatus = MonitorStatus.UNKNOWN
    heartbeat_token: str | None = Field(default=None, exclude=True)
    last_token_rotated_at: datetime | None = None
    token_expires_at: datetime | None = None
    last_heartbeat_received_at: datetime | None = None
    heartbeat_count: int = 0