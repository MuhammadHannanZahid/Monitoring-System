from pydantic import BaseModel
from app.shared.models.monitor_state import MonitorStateModel
from app.shared.enums import WebsiteStatus
from app.modules.monitor_state.enums import MonitorTransition

class MonitorStateResult(BaseModel):
    state: MonitorStateModel
    previous_status: WebsiteStatus
    current_status: WebsiteStatus
    transition: MonitorTransition