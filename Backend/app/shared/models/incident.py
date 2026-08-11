from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict
from app.shared.models.base_monitor import MonitorType

class IncidentModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: str | None = None
    monitor_id: str
    monitor_type: MonitorType
    started_at: datetime
    resolved_at: datetime | None = None
    reason: str
    is_resolved: bool = False

    @property
    def duration_seconds(self) -> int:
        end = self.resolved_at or datetime.now(timezone.utc)
        return int((end - self.started_at).total_seconds())
