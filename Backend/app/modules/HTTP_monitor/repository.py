from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.shared.database_constants import Collections
from app.shared.models.HTTP_monitor import HTTP_monitorModel
from app.shared.enums import HTTP_monitorStatus

class HTTP_monitorRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database[Collections.HTTP_MONITORS]

    async def create_HTTP_monitor(self, HTTP_monitor: HTTP_monitorModel) -> str:
        document = HTTP_monitor.model_dump()
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_by_id(self, HTTP_monitor_id: str) -> HTTP_monitorModel | None:
        try:
            object_id = ObjectId(HTTP_monitor_id)
        except InvalidId:
            return None

        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return HTTP_monitorModel(**document)

    async def get_by_name(self, name: str) -> HTTP_monitorModel | None:
        document = await self.collection.find_one({"name": name})

        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return HTTP_monitorModel(**document)

    async def list_monitors(self) -> list[HTTP_monitorModel]:
        cursor = self.collection.find().sort("created_at", -1)

        monitors = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            monitors.append(HTTP_monitorModel(**document))
        return monitors

    async def update_HTTP_monitor(self, HTTP_monitor_id: str, update_data: dict) -> bool:
        try:
            object_id = ObjectId(HTTP_monitor_id)
        except InvalidId:
            return False

        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one({"_id": object_id}, {"$set": update_data})
        return result.modified_count > 0

    async def delete_HTTP_monitor(self, HTTP_monitor_id: str) -> bool:
        try:
            object_id = ObjectId(HTTP_monitor_id)
        except InvalidId:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def set_active(self, HTTP_monitor_id: str, is_active: bool) -> bool:
        return await self.update_HTTP_monitor(HTTP_monitor_id, {"is_active": is_active})

    async def get_by_url(self, url: str) -> HTTP_monitorModel | None:
        document = await self.collection.find_one({"url": url})
        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return HTTP_monitorModel(**document)

    async def count_similar_names(self, base_name: str) -> int:
        return await self.collection.count_documents({"name": {"$regex": f"^{base_name}( \\d+)?$"}})

    async def update_monitoring_result(self, monitor_id: str, status: HTTP_monitorStatus, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
        try:
            object_id = ObjectId(monitor_id)

        except InvalidId:
            return False

        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": status,
                    "last_status_code": status_code,
                    "last_response_time_ms": response_time_ms,
                    "last_checked_at": checked_at,
                    "updated_at": checked_at,
                }
            },
        )
        return result.modified_count > 0

    async def count_all(self) -> int:
        return await self.collection.count_documents({})

    async def count_active(self) -> int:
        return await self.collection.count_documents({"is_active": True})

    async def count_inactive(self) -> int:
        return await self.collection.count_documents({"is_active": False})

    async def count_by_status(self, status: HTTP_monitorStatus) -> int:
        return await self.collection.count_documents({"status": status})

    async def get_dashboard_counts(self) -> dict[str, int]:
        total = await self.collection.count_documents({})
        active = await self.collection.count_documents({"is_active": True})
        inactive = await self.collection.count_documents({"is_active": False})
        up = await self.collection.count_documents({"status": HTTP_monitorStatus.UP})
        down = await self.collection.count_documents({"status": HTTP_monitorStatus.DOWN})
        unknown = await self.collection.count_documents({"status": HTTP_monitorStatus.UNKNOWN})

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "up": up,
            "down": down,
            "unknown": unknown,
        }

    async def update_monitor_state(self, HTTP_monitor_id: str, *, status: HTTP_monitorStatus, consecutive_failures: int, consecutive_successes: int, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
        try:
            object_id = ObjectId(HTTP_monitor_id)
        except InvalidId:
            return False

        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": status,
                    "last_status_code": status_code,
                    "last_response_time_ms": response_time_ms,
                    "last_checked_at": checked_at,
                    "updated_at": checked_at,
                    "consecutive_failures": consecutive_failures,
                    "consecutive_successes": consecutive_successes,
                }
            },
        )

        return result.modified_count > 0

def get_HTTP_monitor_repository(database: AsyncIOMotorDatabase = Depends(get_database)) -> HTTP_monitorRepository:
    return HTTP_monitorRepository(database)