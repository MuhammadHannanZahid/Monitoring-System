from datetime import datetime, timezone
from app.core.logger import get_logger
from app.modules.incident.repository import IncidentRepository
from app.shared.models.incident import IncidentModel
from app.shared.enums import MonitorType

logger = get_logger(__name__)


class IncidentService:
    def __init__(self, repository: IncidentRepository):
        self.repository = repository

    async def open_incident(self, monitor_id: str, monitor_type: MonitorType, reason: str | None = None) -> None:
        active = await self.repository.get_active_incident(monitor_id, monitor_type)

        if active is not None:
            return

        now = datetime.now(timezone.utc)

        incident = IncidentModel(
            monitor_id=monitor_id,
            monitor_type=monitor_type,
            started_at=now,
            resolved_at=None,
            is_resolved=False,
            reason=reason,
        )

        incident.id = await self.repository.create_incident(incident)
        logger.info("Incident opened for monitor %s. Reason %s", monitor_id, reason)

    async def resolve_incident(self, monitor_id: str, monitor_type: MonitorType) -> None:
        incident = await self.repository.get_active_incident(monitor_id, monitor_type)

        if incident is None:
            return

        await self.repository.resolve_incident(incident.id)
        logger.info("Incident resolved for monitor %s.", monitor_id)

    async def list_incidents(self) -> list[IncidentModel]:
        return await self.repository.list_incidents()

    async def list_by_monitor(self, monitor_id: str) -> list[IncidentModel]:
        return await self.repository.list_by_monitor(monitor_id)

    async def get_incident(self, incident_id: str) -> IncidentModel | None:
        return await self.repository.get_by_id(incident_id)

    async def get_active_incident(self, monitor_id: str, monitor_type: MonitorType) -> IncidentModel | None:
        return await self.repository.get_active_incident(monitor_id, monitor_type)

    async def recent(self, limit: int = 10) -> list[IncidentModel]:
        return await self.repository.get_recent(limit)