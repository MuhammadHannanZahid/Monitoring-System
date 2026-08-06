from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.shared.database_constants import Collections
from app.shared.models.ping_monitor import PingMonitorModel
from datetime import datetime
from app.shared.enums import MonitorStatus

class PingMonitorRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database[Collections.PING_MONITORS]

    def _to_object_id(self, monitor_id: str) -> ObjectId | None:
        try:
            return ObjectId(monitor_id)
        except InvalidId:
            return None

    def _to_model(self, document: dict | None) -> PingMonitorModel | None:
        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return PingMonitorModel(**document)

    async def create(self, monitor: PingMonitorModel) -> str:
        document = monitor.model_dump(exclude_none=True)
        document.pop("id", None)

        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_by_id(self, monitor_id: str) -> PingMonitorModel | None:
        object_id = self._to_object_id(monitor_id)

        if object_id is None:
            return None

        document = await self.collection.find_one(
            {"_id": object_id}
        )

        return self._to_model(document)

    async def list_monitors(
        self,
    ) -> list[PingMonitorModel]:

        cursor = self.collection.find()

        monitors = []

        async for document in cursor:
            monitor = self._to_model(document)
            if monitor is not None:
                monitors.append(monitor)

        return monitors

    async def list_active_monitors(self) -> list[PingMonitorModel]:
        cursor = self.collection.find({"is_active": True})
        monitors = []

        async for document in cursor:
            monitor = self._to_model(document)
            if monitor is not None:
                monitors.append(monitor)

        return monitors

    async def update_monitoring_result(self, monitor_id: str, status: MonitorStatus, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
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
                    "last_response_time_ms": response_time_ms,
                    "last_checked_at": checked_at,
                }
            },
        )
        return result.modified_count > 0

    async def update(self, monitor: PingMonitorModel) -> bool:
        object_id = self._to_object_id(monitor.id)

        if object_id is None:
            return False

        document = monitor.model_dump()
        document.pop("id", None)

        result = await self.collection.replace_one({"_id": object_id}, document)
        return result.modified_count > 0

    async def set_active(self, monitor_id: str, is_active: bool) -> bool:
        object_id = self._to_object_id(monitor_id)

        if object_id is None:
            return False

        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "is_active": is_active,
                }
            },
        )
        return result.modified_count > 0

    async def delete(self, monitor_id: str) -> bool:
        object_id = self._to_object_id(monitor_id)

        if object_id is None:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def get_by_name(self, name: str) -> PingMonitorModel | None:
        document = await self.collection.find_one({"name": name})
        return self._to_model(document)