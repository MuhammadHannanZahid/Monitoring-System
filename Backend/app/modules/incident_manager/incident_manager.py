from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine
from app.core.logger import get_logger
from app.service.constants import Collections
from app.service.mongo_db.shared_models.db_monitoring_controller_model import MonitorType
from app.service.mongo_db.shared_models.db_incident_model import IncidentModel

logger = get_logger(__name__)

class IncidentManager:
    def __init__(self, engine: AIOEngine):
        self.collection = engine.database[Collections.INCIDENTS]

    async def open_incident(self, monitor_id: str, monitor_type: MonitorType, reason: str | None = None) -> None:
        active = await self.get_active_incident(monitor_id, monitor_type)
        if active is not None:
            return

        incident = IncidentModel(
            monitor_id=monitor_id,
            monitor_type=monitor_type,
            started_at=datetime.now(timezone.utc),
            resolved_at=None,
            is_resolved=False,
            reason=reason,
        )
        document = incident.model_dump()
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        incident.id = str(result.inserted_id)
        logger.info("Incident opened for monitor %s. Reason %s", monitor_id, reason)

    async def resolve_incident(self, monitor_id: str, monitor_type: MonitorType) -> bool:
        incident = await self.get_active_incident(monitor_id, monitor_type)
        if incident is None:
            return False

        try:
            object_id = ObjectId(incident.id)
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

    async def count_open(self) -> int:
        return await self.collection.count_documents({"is_resolved": False})

    async def get_recent(self, limit: int = 10) -> list[IncidentModel]:
        cursor = self.collection.find().sort("started_at", -1).limit(limit)
        incidents = []
        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            incidents.append(IncidentModel(**document))
        return incidents
