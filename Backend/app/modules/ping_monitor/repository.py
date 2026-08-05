from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.shared.database_constants import Collections
from app.shared.models.ping_monitor import PingMonitorModel


class PingMonitorRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database[Collections.PING_MONITORS]

    async def create(self, monitor: PingMonitorModel) -> str:
        document = monitor.model_dump()
        document.pop("id", None)

        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_by_id(
        self,
        monitor_id: str,
    ) -> PingMonitorModel | None:

        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return None

        document = await self.collection.find_one(
            {"_id": object_id}
        )

        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return PingMonitorModel(**document)

    async def list_monitors(
        self,
    ) -> list[PingMonitorModel]:

        cursor = self.collection.find()

        monitors = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            monitors.append(
                PingMonitorModel(**document)
            )

        return monitors

    async def list_active_monitors(self) -> list[PingMonitorModel]:
        cursor = self.collection.find({"is_active": True})
        monitors = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            monitors.append(PingMonitorModel(**document))
        return monitors

    async def update_monitoring_result(self, monitor_id: str, status, status_code: int | None, response_time_ms: int | None, checked_at) -> bool:
        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return False

        result = await self.collection.update_one(
            {
                "_id": object_id,
            },
            {
                "$set": {
                    "status": status,
                    "last_status_code": status_code,
                    "last_response_time_ms": response_time_ms,
                    "last_checked_at": checked_at,
                }
            },
        )
        return result.modified_count > 0

    async def update(self, monitor: PingMonitorModel) -> bool:
        try:
            object_id = ObjectId(monitor.id)
        except InvalidId:
            return False

        document = monitor.model_dump()
        document.pop("id", None)

        result = await self.collection.replace_one({"_id": object_id}, document)
        return result.modified_count > 0

    async def delete(self, monitor_id: str) -> bool:
        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0