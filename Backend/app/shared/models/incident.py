from datetime import datetime
from pydantic import BaseModel, ConfigDict

class IncidentModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: str | None = None
    website_id: str
    started_at: datetime
    resolved_at: datetime | None = None
    reason: str
    is_resolved: bool = False