from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.core.logger import get_logger
from app.shared.constants import Collections
from app.shared.models.incident import IncidentModel
from app.shared.models.base_monitor import MonitorType

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

    async def resolve_incident(self, monitor_id: str, monitor_type: MonitorType):
        incident = await self.repository.get_active_incident(
            monitor_id, monitor_type)

        if incident is None:
            return

        await self.repository.resolve_incident(
            incident.id, monitor_type)

    async def get_active_incident(self, monitor_id: str, monitor_type: MonitorType) -> IncidentModel | None:
        return await self.repository.get_active_incident(monitor_id, monitor_type)


class IncidentRepository:
    def __init__(self, engine: AIOEngine):
        self.engine = engine
        self.collection = engine.database[Collections.INCIDENTS]

    async def create_incident(self, incident: IncidentModel) -> str:
        document = incident.model_dump()
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_active_incident(self, monitor_id: str, monitor_type: MonitorType) -> IncidentModel | None:
        document = await self.collection.find_one(
            {
                "monitor_id": monitor_id,
                "monitor_type": monitor_type,
                "resolved_at": None,
            }
        )

        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return IncidentModel(**document)

    async def resolve_incident(self, incident_id: str, monitor_type: MonitorType) -> bool:
        try:
            object_id = ObjectId(incident_id)
        except InvalidId:
            return False

        result = await self.collection.update_one(
            {
                "_id": object_id,
                "monitor_type": monitor_type,
                "resolved_at": None,
            },
            {
                "$set": {
                    "is_resolved": True,
                    "resolved_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    async def count_open(self) -> int:
        return await self.collection.count_documents({"is_resolved": False})

    async def get_recent(self, limit: int = 10) -> list[IncidentModel]:
        cursor = (self.collection.find().sort("started_at", -1).limit(limit))

        incidents = []
        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            incidents.append(IncidentModel(**document))

        return incidents

def get_incident_repository(
    engine: AIOEngine = Depends(get_engine),
) -> IncidentRepository:
    return IncidentRepository(engine)
