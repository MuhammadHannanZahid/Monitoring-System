from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.shared.database_constants import Collections
from app.shared.models.incident import IncidentModel

class IncidentRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database[Collections.INCIDENTS]

    async def create_incident(self, incident: IncidentModel) -> str:
        document = incident.model_dump()
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_active_incident(self, website_id: str) -> IncidentModel | None:
        document = await self.collection.find_one(
            {
                "website_id": website_id,
                "is_resolved": False,
            }
        )
        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return IncidentModel(**document)


    async def resolve_incident(self, incident_id: str) -> bool:
        try:
            object_id = ObjectId(incident_id)
        except InvalidId:
            return False

        result = await self.collection.update_one(
            {"_id": object_id},
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


    async def list_by_website(self, website_id: str) -> list[IncidentModel]:
        cursor = self.collection.find({"website_id": website_id}).sort("started_at", -1)
        incidents = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            incidents.append(IncidentModel(**document))
        return incidents

    async def count_open(self) -> int:
        return await self.collection.count_documents({"resolved_at": None})

    async def get_recent(self, limit: int = 10) -> list[IncidentModel]:
        cursor = (self.collection.find().sort("started_at", -1).limit(limit))

def get_incident_repository(database: AsyncIOMotorDatabase = Depends(get_database)) -> IncidentRepository:
    return IncidentRepository(database)