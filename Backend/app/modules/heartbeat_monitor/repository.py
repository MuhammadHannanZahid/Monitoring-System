from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.shared.models.heartbeat_monitor import HeartbeatMonitorModel
from app.shared.models.base_monitor import MonitorStatus

class HeartbeatMonitorRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database["heartbeat_monitors"]

    @staticmethod
    def _to_object_id(monitor_id: str) -> ObjectId | None:
        try:
            return ObjectId(monitor_id)
        except (InvalidId, TypeError):
            return None

    @staticmethod
    def _to_model(document: dict | None) -> HeartbeatMonitorModel | None:
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return HeartbeatMonitorModel(**document)

    async def create(self, monitor: HeartbeatMonitorModel) -> str:
        document = monitor.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_by_id(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        object_id = self._to_object_id(monitor_id)
        if object_id is None:
            return None
        return self._to_model(await self.collection.find_one({"_id": object_id}))

    async def get_by_name(self, name: str) -> HeartbeatMonitorModel | None:
        return self._to_model(await self.collection.find_one({"name": name}))

    async def get_by_token_hash(self, token_hash: str) -> HeartbeatMonitorModel | None:
        return self._to_model(
            await self.collection.find_one({"heartbeat_token_hash": token_hash})
        )

    async def list_monitors(self) -> list[HeartbeatMonitorModel]:
        monitors: list[HeartbeatMonitorModel] = []
        async for document in self.collection.find().sort("created_at", -1):
            monitor = self._to_model(document)
            if monitor is not None:
                monitors.append(monitor)
        return monitors

    async def list_active_monitors(self) -> list[HeartbeatMonitorModel]:
        monitors: list[HeartbeatMonitorModel] = []
        async for document in self.collection.find({"is_active": True}):
            monitor = self._to_model(document)
            if monitor is not None:
                monitors.append(monitor)
        return monitors

    async def update(self, monitor: HeartbeatMonitorModel) -> bool:
        object_id = self._to_object_id(monitor.id)
        if object_id is None:
            return False
        update_data = monitor.model_dump(by_alias=True, exclude={"id"})
        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": update_data,
                "$unset": {"check_interval": ""},
            },
        )
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
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    async def update_last_heartbeat(
        self,
        monitor_id: str,
        received_at: datetime | None = None,
    ) -> bool:
        object_id = self._to_object_id(monitor_id)
        if object_id is None:
            return False
        now = received_at or datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "last_heartbeat_at": now,
                    "updated_at": now,
                },
                "$inc": {
                    "heartbeat_count": 1,
                },
            },
        )
        return result.modified_count > 0

    async def delete(self, monitor_id: str) -> bool:
        object_id = self._to_object_id(monitor_id)
        if object_id is None:
            return False
        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def update_monitoring_result(self, monitor_id: str, status: MonitorStatus, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
        object_id = self._to_object_id(monitor_id)
        if object_id is None:
            return False
        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": status,
                    "last_checked_at": checked_at,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        return result.modified_count > 0

    async def create_indexes(self):
        await self.collection.create_index("heartbeat_token_hash", unique=True)
        await self.collection.create_index("is_active")
        await self.collection.create_index("name")
