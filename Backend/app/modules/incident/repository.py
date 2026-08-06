from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.shared.database_constants import Collections
from app.shared.models.incident import IncidentModel
from app.shared.enums import MonitorType

class IncidentRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database[Collections.INCIDENTS]

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

    async def get_by_id(self, incident_id: str) -> IncidentModel | None:
        try:
            object_id = ObjectId(incident_id)
        except InvalidId:
            return None

        document = await self.collection.find_one({"_id": object_id})

        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return IncidentModel(**document)

    async def list_incidents(self) -> list[IncidentModel]:
        cursor = self.collection.find().sort("started_at", -1)
        incidents = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            incidents.append(IncidentModel(**document))
        return incidents

    async def count_open(self) -> int:
        return await self.collection.count_documents({"is_resolved": False})

    async def get_recent(self, limit: int = 10) -> list[IncidentModel]:
        cursor = (self.collection.find().sort("started_at", -1).limit(limit))

        incidents = []
        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            incidents.append(IncidentModel(**document))

        return incidents

    async def count_open_by_monitor(
            self,
    ) -> dict[str, int]:

        pipeline = [

            {
                "$match": {
                    "resolved_at": None
                }
            },

            {
                "$group": {

                    "_id": "$monitor_id",

                    "count": {
                        "$sum": 1
                    }

                }
            }

        ]

        result = await (
            self.collection
            .aggregate(pipeline)
            .to_list(None)
        )

        return {
            item["_id"]: item["count"]
            for item in result
        }

def get_incident_repository(database: AsyncIOMotorDatabase = Depends(get_database)) -> IncidentRepository:
    return IncidentRepository(database)