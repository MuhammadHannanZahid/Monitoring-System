from __future__ import annotations
import ipaddress
from datetime import datetime, timezone
from urllib.parse import urlparse
from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine
import app.modules.monitor.scheduler as scheduler_state
from app.service.constants import Collections
from app.service.mongo_db.shared_models.models.base_monitor import MonitorStatus, MonitorType
from app.service.mongo_db.shared_models.models.ping_monitor import PingMonitorModel

class PingMonitorService:
    def __init__(self, engine: AIOEngine):
        self.collection = engine.database[Collections.PING_MONITORS]

    async def create_monitor(self, name: str, host: str, check_interval: int, timeout: int, expected_response_time_ms: int | None, created_by: str | None = None) -> PingMonitorModel:
        now = datetime.now(timezone.utc)
        monitor = PingMonitorModel(
            name=name,
            host=self._normalize_host(host),
            monitor_type=MonitorType.PING,
            check_interval=check_interval,
            timeout=timeout,
            expected_response_time_ms=expected_response_time_ms,
            created_by=created_by,
            is_active=True,
            status=MonitorStatus.UNKNOWN,
            created_at=now,
            updated_at=now,
        )
        document = monitor.model_dump(exclude_none=True)
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        monitor.id = str(result.inserted_id)

        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(monitor)
        return monitor

    async def get_monitor(self, monitor_id: str) -> PingMonitorModel | None:
        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return None
        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return PingMonitorModel(**document)

    async def list_monitors(self) -> list[PingMonitorModel]:
        monitors = []
        async for document in self.collection.find():
            document["id"] = str(document.pop("_id"))
            monitors.append(PingMonitorModel(**document))
        return monitors

    async def update_monitor(self, monitor_id: str, name: str | None = None, host: str | None = None, check_interval: int | None = None, timeout: int | None = None, expected_response_time_ms: int | None = None) -> PingMonitorModel | None:
        monitor = await self.get_monitor(monitor_id)
        if monitor is None:
            return None
        if name is not None:
            monitor.name = name
        if host is not None:
            monitor.host = self._normalize_host(host)
        if check_interval is not None:
            monitor.check_interval = check_interval
        if timeout is not None:
            monitor.timeout = timeout
        if expected_response_time_ms is not None:
            monitor.expected_response_time_ms = expected_response_time_ms
        monitor.updated_at = datetime.now(timezone.utc)

        document = monitor.model_dump()
        document.pop("id", None)
        await self.collection.replace_one(
            {"_id": ObjectId(monitor_id)},
            document,
        )
        return monitor

    async def delete_monitor(self, monitor_id: str) -> bool:
        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return False
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor_id)
        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def update_monitoring_result(self, monitor_id: str, status: MonitorStatus, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return False
        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": status,
                    "last_response_time_ms": response_time_ms,
                    "last_checked_at": checked_at,
                }
            },
        )
        return result.modified_count > 0

    @staticmethod
    def _normalize_host(host: str) -> str:
        host = host.strip()
        if "://" in host:
            parsed = urlparse(host)
            if parsed.hostname:
                host = parsed.hostname
        host = host.rstrip("/")
        if ":" in host:
            try:
                ipaddress.ip_address(host)
            except ValueError:
                host = host.split(":")[0]
        return host.lower()