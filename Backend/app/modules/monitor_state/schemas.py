from pydantic import BaseModel
from app.shared.models.monitor_state import MonitorStateModel
from app.shared.enums import HTTP_monitorStatus
from app.modules.monitor_state.enums import MonitorTransition

class MonitorStateResult(BaseModel):
    state: MonitorStateModel
    previous_status: HTTP_monitorStatus
    current_status: HTTP_monitorStatus
    transition: MonitorTransition