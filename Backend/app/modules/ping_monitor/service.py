from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine

from app.shared.constants import Collections
from app.shared.models.base_monitor import MonitorStatus, MonitorType
from app.shared.models.ping_monitor import PingMonitorModel, PingMonitorResponse
from urllib.parse import urlparse
import ipaddress
import app.core.scheduler as scheduler_state
from app.core.logger import get_logger

logger = get_logger(__name__)

class PingMonitorService:
    def __init__(self, repository: PingMonitorRepository):
        self.repository = repository

    async def create_monitor(self, name: str, host: str, check_interval: int, timeout: int, expected_response_time_ms: int | None, created_by: str | None = None) -> PingMonitorModel:
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
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        monitor.id = await self.repository.create(monitor)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(monitor)
        return monitor

    async def get_monitor(self, monitor_id: str) -> PingMonitorModel | None:
        return await self.repository.get_by_id(monitor_id)

    async def list_monitors(self) -> list[PingMonitorModel]:
        return await self.repository.list_monitors()

    async def update_monitor(self, monitor_id: str, name: str | None = None, host: str | None = None, check_interval: int | None = None, timeout: int | None = None, expected_response_time_ms: int | None = None) -> PingMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)

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
        await self.repository.update(monitor)
        return monitor

    async def delete_monitor(self, monitor_id: str) -> bool:
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor_id)
        return await self.repository.delete(monitor_id)

    def _normalize_host(self, host: str) -> str:
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

    def to_response(self, monitor: PingMonitorModel) -> PingMonitorResponse:
        return PingMonitorResponse(
            id=monitor.id,
            name=monitor.name,
            host=monitor.host,
            check_interval=monitor.check_interval,
            timeout=monitor.timeout,
            expected_response_time_ms=monitor.expected_response_time_ms,
            is_active=monitor.is_active,
            created_by=monitor.created_by,
            created_at=monitor.created_at,
            updated_at=monitor.updated_at,
            last_checked_at=monitor.last_checked_at,
            last_status_code=monitor.last_status_code,
            last_response_time_ms=monitor.last_response_time_ms,
            status=monitor.status,
        )

    def to_response_list(
        self,
        monitors: list[PingMonitorModel],
    ) -> list[PingMonitorResponse]:
        return [
            self.to_response(monitor)
            for monitor in monitors
        ]


class PingMonitorRepository:
    def __init__(self, engine: AIOEngine):
        self.engine = engine
        self.collection = engine.database[Collections.PING_MONITORS]

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

    async def delete(self, monitor_id: str) -> bool:
        object_id = self._to_object_id(monitor_id)

        if object_id is None:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0
