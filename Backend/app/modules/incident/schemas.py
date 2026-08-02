from datetime import datetime
from pydantic import BaseModel

class IncidentResponse(BaseModel):
    id: str
    HTTP_monitor_id: str
    started_at: datetime
    resolved_at: datetime | None
    is_resolved: bool
    reason: str | None


class IncidentListResponse(BaseModel):
    list[IncidentResponse]