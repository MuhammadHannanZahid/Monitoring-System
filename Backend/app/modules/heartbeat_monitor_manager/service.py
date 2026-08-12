from __future__ import annotations
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine
import app.modules.monitoring_controller.scheduler as scheduler_state
from app.service.constants import Collections
from app.service.mongo_db.shared_models.db_monitoring_controller_model import MonitorStatus, MonitorType
from app.service.mongo_db.shared_models.db_heartbeat_monitor_model import HeartbeatMonitorModel

if TYPE_CHECKING:
    from app.modules.monitoring_controller.service import MonitorService

class HeartbeatMonitorService:
    def __init__(self, engine: AIOEngine, monitor_service: MonitorService | None = None):
        self.collection = engine.database[Collections.HEARTBEAT_MONITORS]
        self.monitor_service = monitor_service

    async def create_monitor(self, name: str, expected_heartbeat_interval: int, grace_period: int, created_by: str | None = None) -> HeartbeatMonitorModel:
        token = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        monitor = HeartbeatMonitorModel(
            name=name,
            monitor_type=MonitorType.HEARTBEAT,
            heartbeat_token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expected_heartbeat_interval=expected_heartbeat_interval,
            grace_period=grace_period,
            created_by=created_by,
            is_active=True,
            status=MonitorStatus.UNKNOWN,
            last_token_rotated_at=now,
            token_expires_at=now + timedelta(days=90),
            created_at=now,
            updated_at=now,
        )
        document = monitor.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(document)
        monitor.id = str(result.inserted_id)
        monitor.heartbeat_token = token
        return monitor

    async def get_monitor(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        try:
            object_id = ObjectId(monitor_id)
        except (InvalidId, TypeError):
            return None
        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return HeartbeatMonitorModel(**document)

    async def list_monitors(self) -> list[HeartbeatMonitorModel]:
        monitors = []
        async for document in self.collection.find().sort("created_at", -1):
            document["id"] = str(document.pop("_id"))
            monitors.append(HeartbeatMonitorModel(**document))
        return monitors

    async def update_monitor(self, monitor_id: str, name: str | None = None, expected_heartbeat_interval: int | None = None, grace_period: int | None = None) -> HeartbeatMonitorModel | None:
        monitor = await self.get_monitor(monitor_id)
        if monitor is None:
            return None
        if name is not None:
            monitor.name = name
        if expected_heartbeat_interval is not None:
            monitor.expected_heartbeat_interval = expected_heartbeat_interval
        if grace_period is not None:
            monitor.grace_period = grace_period
        monitor.updated_at = datetime.now(timezone.utc)

        update_data = monitor.model_dump(by_alias=True, exclude={"id"})
        await self.collection.update_one(
            {"_id": ObjectId(monitor_id)},
            {
                "$set": update_data,
                "$unset": {"check_interval": ""},
            },
        )
        updated = await self.get_monitor(monitor_id)
        if (
            updated is not None
            and updated.is_active
            and updated.last_heartbeat_at is not None
            and scheduler_state.scheduler is not None
        ):
            await scheduler_state.scheduler.stop_worker(monitor_id)
            await scheduler_state.scheduler.start_worker(updated)
        return updated

    async def delete_monitor(self, monitor_id: str) -> bool:
        try:
            object_id = ObjectId(monitor_id)
        except (InvalidId, TypeError):
            return False
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor_id)
        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def regenerate_token(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        monitor = await self.get_monitor(monitor_id)
        if monitor is None:
            return None
        new_token = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        monitor.heartbeat_token_hash = hashlib.sha256(new_token.encode()).hexdigest()
        monitor.last_token_rotated_at = now
        monitor.token_expires_at = now + timedelta(days=90)
        monitor.updated_at = now

        update_data = monitor.model_dump(by_alias=True, exclude={"id"})
        await self.collection.update_one(
            {"_id": ObjectId(monitor_id)},
            {
                "$set": update_data,
                "$unset": {"check_interval": ""},
            },
        )
        monitor.heartbeat_token = new_token
        return monitor

    async def receive_heartbeat(self, token: str) -> HeartbeatMonitorModel | None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        document = await self.collection.find_one(
            {"heartbeat_token_hash": token_hash}
        )
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        monitor = HeartbeatMonitorModel(**document)
        now = datetime.now(timezone.utc)
        if not monitor.is_active:
            return None
        if monitor.token_expires_at is not None and now > monitor.token_expires_at:
            return None

        await self.collection.update_one(
            {"_id": ObjectId(monitor.id)},
            {
                "$set": {
                    "last_heartbeat_at": now,
                    "updated_at": now,
                },
                "$inc": {"heartbeat_count": 1},
            },
        )
        await self._get_monitor_service().process_heartbeat(monitor)
        updated = await self.get_monitor(monitor.id)
        if updated is not None and scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(updated)
        return updated

    async def update_monitoring_result(self, monitor_id: str, status: MonitorStatus, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
        try:
            object_id = ObjectId(monitor_id)
        except (InvalidId, TypeError):
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

    def _get_monitor_service(self) -> MonitorService:
        if self.monitor_service is not None:
            return self.monitor_service
        if scheduler_state.scheduler is None:
            raise RuntimeError("The monitor scheduler has not been initialized.")
        return scheduler_state.scheduler.monitor_service