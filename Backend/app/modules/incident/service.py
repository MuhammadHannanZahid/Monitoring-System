from datetime import datetime, timezone
from app.core.logger import get_logger
from app.modules.incident.repository import IncidentRepository
from app.shared.models.incident import IncidentModel

logger = get_logger(__name__)


class IncidentService:
    def __init__(self, repository: IncidentRepository):
        self.repository = repository

    async def open_incident(self, website_id: str, reason: str | None = None) -> None:
        active = await self.repository.get_active_incident(website_id)

        if active is not None:
            return

        now = datetime.now(timezone.utc)

        incident = IncidentModel(
            website_id=website_id,
            started_at=now,
            resolved_at=None,
            is_resolved=False,
            reason=reason,
        )

        incident.id = await self.repository.create_incident(incident)
        logger.info("Incident opened for website %s.", website_id)

    async def resolve_incident(self, website_id: str) -> None:
        incident = await self.repository.get_active_incident(website_id)

        if incident is None:
            return

        await self.repository.resolve_incident(incident.id)
        logger.info("Incident resolved for website %s.", website_id)


    async def list_incidents(self):
        return await self.repository.list_incidents()

    async def list_by_website(self, website_id: str):
        return await self.repository.list_by_website(website_id)

    async def get_incident(self, incident_id: str):
        return await self.repository.get_by_id(incident_id)

class MonitorService:
    def __init__(self, website_repository: WebsiteRepository, incident_service: IncidentService):
        self.website_repository = website_repository
        self.incident_service = incident_service