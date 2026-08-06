from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.shared.models.heartbeat_monitor import HeartbeatMonitorModel
from app.shared.enums import MonitorStatus

class HeartbeatMonitorRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database["heartbeat_monitors"]

    async def create(self, monitor: HeartbeatMonitorModel) -> str:
        document = monitor.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_by_id(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        document = await self.collection.find_one({"_id": ObjectId(monitor_id)})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return HeartbeatMonitorModel(**document)

    async def get_by_name(self, name: str) -> HeartbeatMonitorModel | None:
        document = await self.collection.find_one({"name": name})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return HeartbeatMonitorModel(**document)

    async def get_by_token_hash(self, token_hash:str) -> HeartbeatMonitorModel | None:
        document = await self.collection.find_one({"heartbeat_token_hash": token_hash})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return HeartbeatMonitorModel(**document)

    async def list_monitors(self) -> list[HeartbeatMonitorModel]:
        monitors: list[HeartbeatMonitorModel] = []
        async for document in self.collection.find():
            document["id"] = str(document.pop("_id"))
            monitors.append(HeartbeatMonitorModel(**document))
        return monitors

    async def list_active_monitors(self) -> list[HeartbeatMonitorModel]:
        monitors: list[HeartbeatMonitorModel] = []
        async for document in self.collection.find({"is_active": True}):
            document["id"] = str(document.pop("_id"))
            monitors.append(HeartbeatMonitorModel(**document))
        return monitors

    async def update(self, monitor: HeartbeatMonitorModel) -> bool:
        update_data = monitor.model_dump(by_alias=True, exclude={"id"})
        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {
                "_id": ObjectId(monitor.id),
            },
            {
                "$set": update_data,
            },
        )
        return result.modified_count > 0

    async def set_active(self, monitor_id: str, is_active: bool) -> bool:
        result = await self.collection.update_one(
            {
                "_id": ObjectId(monitor_id),
            },
            {
                "$set": {
                    "is_active": is_active,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    async def update_last_heartbeat(self, monitor_id: str) -> bool:
        now = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {
                "_id": ObjectId(monitor_id),
            },
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
        result = await self.collection.delete_one({"_id": ObjectId(monitor_id)})
        return result.deleted_count > 0

    async def update_monitoring_result(self, monitor_id: str, status: MonitorStatus, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
        result = await self.collection.update_one(
            {
                "_id": ObjectId(monitor_id),
            },
            {
                "$set": {
                    "status": status,
                    "status_code": status_code,
                    "response_time_ms": response_time_ms,
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