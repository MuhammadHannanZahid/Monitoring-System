from datetime import datetime
from pydantic import BaseModel
from app.modules.monitor_state.enums import MonitorTransition
from app.shared.models.base_monitor import MonitorStatus, MonitorType

class MonitorStateModel(BaseModel):
    id: str | None = None
    monitor_id: str
    monitor_type: MonitorType
    status: MonitorStatus = MonitorStatus.UNKNOWN
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_checked_at: datetime | None = None
    last_status_code: int | None = None
    last_response_time_ms: int | None = None


class MonitorStateResult(BaseModel):
    state: MonitorStateModel
    previous_status: MonitorStatus
    current_status: MonitorStatus
    transition: MonitorTransition
