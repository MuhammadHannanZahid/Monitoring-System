from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import uuid

from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine

import app.core.scheduler as scheduler_state
from app.shared.models.base_monitor import MonitorStatus, MonitorType
from app.shared.models.heartbeat_monitor import (
    HeartbeatMonitorModel,
)
from app.modules.monitor.service import MonitorService


class HeartbeatMonitorService:
    def __init__(
        self,
        repository: HeartbeatMonitorRepository,
        monitor_service: MonitorService | None = None,
    ):
        self.repository = repository
        self.monitor_service = monitor_service

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _generate_token(self) -> str:
        return uuid.uuid4().hex

    def _get_monitor_service(self) -> MonitorService:
        if self.monitor_service is not None:
            return self.monitor_service
        if scheduler_state.scheduler is None:
            raise RuntimeError("The monitor scheduler has not been initialized.")
        return scheduler_state.scheduler.monitor_service

    async def create_monitor(
        self,
        name: str,
        expected_heartbeat_interval: int,
        grace_period: int,
        created_by: str | None = None,
    ) -> HeartbeatMonitorModel:
        token = self._generate_token()
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)
        monitor = HeartbeatMonitorModel(
            name=name,
            monitor_type=MonitorType.HEARTBEAT,
            heartbeat_token_hash=token_hash,
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
        monitor.id = await self.repository.create(monitor)
        monitor.heartbeat_token = token
        return monitor

    async def get_monitor(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        return await self.repository.get_by_id(monitor_id)

    async def list_monitors(self) -> list[HeartbeatMonitorModel]:
        return await self.repository.list_monitors()

    async def update_monitor(
        self,
        monitor_id: str,
        name: str | None = None,
        expected_heartbeat_interval: int | None = None,
        grace_period: int | None = None,
    ) -> HeartbeatMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        if name is not None:
            monitor.name = name
        if expected_heartbeat_interval is not None:
            monitor.expected_heartbeat_interval = expected_heartbeat_interval
        if grace_period is not None:
            monitor.grace_period = grace_period
        monitor.updated_at = datetime.now(timezone.utc)
        await self.repository.update(monitor)
        updated = await self.repository.get_by_id(monitor_id)
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
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor_id)
        return await self.repository.delete(monitor_id)

    async def regenerate_token(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        new_token = self._generate_token()
        now = datetime.now(timezone.utc)
        monitor.heartbeat_token_hash = self._hash_token(new_token)
        monitor.last_token_rotated_at = now
        monitor.token_expires_at = now + timedelta(days=90)
        monitor.updated_at = now
        await self.repository.update(monitor)
        monitor.heartbeat_token = new_token
        return monitor

    async def receive_heartbeat(self, token: str) -> HeartbeatMonitorModel | None:
        token_hash = self._hash_token(token)
        monitor = await self.repository.get_by_token_hash(token_hash)
        now = datetime.now(timezone.utc)
        if monitor is None:
            return None

        if not monitor.is_active:
            return None

        if monitor.token_expires_at is not None and now > monitor.token_expires_at:
            return None

        await self._get_monitor_service().process_heartbeat(monitor)
        updated = await self.repository.get_by_id(monitor.id)
        if updated is not None and scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(updated)
        return updated

class HeartbeatMonitorRepository:
    def __init__(self, engine: AIOEngine):
        self.engine = engine
        self.collection = engine.database["heartbeat_monitors"]

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
