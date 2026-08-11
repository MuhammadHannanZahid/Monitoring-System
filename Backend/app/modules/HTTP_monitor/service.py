from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.shared.constants import Collections
from app.shared.constants import Messages
from app.shared.models.base_monitor import MonitorStatus
from app.shared.exceptions import ConflictError, NotFoundError
from app.shared.models.HTTP_monitor import HTTPMonitorModel, HTTP_monitorResponse
from app.core.logger import get_logger
import app.core.scheduler as scheduler_state

logger = get_logger(__name__)

class HTTP_monitorService:
    def __init__(self, repository: HTTP_monitorRepository):
        self.repository = repository

    async def create_monitor(self, name: str, url: str, check_interval: int, timeout: int, expected_status_code: int, expected_response_time_ms:int) -> HTTPMonitorModel:
        existing_url = await self.repository.get_by_url(url)
        if existing_url is not None:
            logger.warning("Attempted to create HTTP_monitor with existing URL '%s'.", url)
            raise ConflictError(Messages.HTTP_monitor_ALREADY_EXISTS)

        count = await self.repository.count_similar_names(name)
        final_name = name

        if count > 0:
            final_name = f"{name} {count}"
            logger.info("HTTP_monitor name '%s' already exists. Assigned new name '%s'.", name, final_name)

        now = datetime.now(timezone.utc)

        HTTP_monitor = HTTPMonitorModel(
            name=final_name,
            url=url,
            check_interval=check_interval,
            timeout=timeout,
            expected_status_code=expected_status_code,
            status=MonitorStatus.UNKNOWN,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_checked_at=None,
            expected_response_time_ms=expected_response_time_ms,
        )

        HTTP_monitor.id = await self.repository.create(HTTP_monitor)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(HTTP_monitor)
        logger.info("HTTP_monitor '%s' created. URL: %s", HTTP_monitor.name, HTTP_monitor.url)
        return HTTP_monitor

    async def list_monitors(self) -> list[HTTPMonitorModel]:
        return await self.repository.list_monitors()

    async def get_monitor(self, HTTP_monitor_id: str) -> HTTPMonitorModel:
        HTTP_monitor = await self.repository.get_by_id(HTTP_monitor_id)
        if HTTP_monitor is None:
            logger.warning("Requested HTTP_monitor '%s' was not found.", HTTP_monitor_id)
            raise NotFoundError(Messages.monitor_NOT_FOUND)
        return HTTP_monitor

    async def update_monitor(self, HTTP_monitor_id: str, name: str | None, url: str | None, check_interval: int | None, timeout: int | None, expected_status_code: int | None, expected_response_time_ms:int) -> HTTPMonitorModel:
        HTTP_monitor = await self.get_monitor(HTTP_monitor_id)
        update_data = {}
        if name is not None and name != HTTP_monitor.name:
            count = await self.repository.count_similar_names(name)
            if count > 0:
                final_name = f"{name} {count}"
                logger.info("HTTP_monitor name '%s' already exists. Assigned new name '%s' during update for HTTP_monitor ID %s.", name, final_name, HTTP_monitor_id)
                update_data["name"] = final_name
            else:
                update_data["name"] = name

        if url is not None and url != HTTP_monitor.url:
            existing_url = await self.repository.get_by_url(url)
            if existing_url is not None and str(existing_url.id) != str(HTTP_monitor_id):
                logger.warning("Attempted to update HTTP_monitor '%s' with existing URL '%s'.", HTTP_monitor.name, url)
                raise ConflictError(Messages.HTTP_monitor_ALREADY_EXISTS)
            update_data["url"] = url

        if check_interval is not None and check_interval != HTTP_monitor.check_interval:
            update_data["check_interval"] = check_interval

        if timeout is not None and timeout != HTTP_monitor.timeout:
            update_data["timeout"] = timeout

        if expected_status_code is not None and expected_status_code != HTTP_monitor.expected_status_code:
            update_data["expected_status_code"] = expected_status_code

        if expected_response_time_ms is not None and expected_response_time_ms != HTTP_monitor.expected_response_time_ms:
            update_data["expected_response_time_ms"] = expected_response_time_ms

        if update_data:
            await self.repository.update_monitor(HTTP_monitor_id, update_data)
            updated_HTTP_monitor = await self.get_monitor(HTTP_monitor_id)

            if updated_HTTP_monitor.is_active and scheduler_state.scheduler is not None:
                await scheduler_state.scheduler.stop_worker(updated_HTTP_monitor.id)
                await scheduler_state.scheduler.start_worker(updated_HTTP_monitor)
            logger.info("HTTP_monitor '%s' updated. Fields changed: %s", updated_HTTP_monitor.name, ", ".join(update_data.keys()))
            return updated_HTTP_monitor

        return HTTP_monitor

    async def delete_monitor(self, HTTP_monitor_id: str) -> None:
        HTTP_monitor = await self.get_monitor(HTTP_monitor_id)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(HTTP_monitor.id)

        await self.repository.delete_monitor(HTTP_monitor.id)
        logger.info("HTTP_monitor '%s' deleted.", HTTP_monitor.name)

    async def activate_monitor(self, HTTP_monitor_id: str):
        monitor = await self.get_monitor(HTTP_monitor_id)
        await self.repository.set_active(monitor.id, True)
        updated = await self.get_monitor(HTTP_monitor_id)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(updated)
        return updated

    async def deactivate_monitor(self, HTTP_monitor_id: str):
        monitor = await self.get_monitor(HTTP_monitor_id)
        await self.repository.set_active(monitor.id, False)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor.id)
        return await self.get_monitor(HTTP_monitor_id)

    def to_response(self, http_monitor: HTTPMonitorModel) -> HTTP_monitorResponse:
        return HTTP_monitorResponse(
            id=http_monitor.id,
            name=http_monitor.name,
            url=http_monitor.url,
            check_interval=http_monitor.check_interval,
            timeout=http_monitor.timeout,
            expected_status_code=http_monitor.expected_status_code,
            is_active=http_monitor.is_active,
            created_at=http_monitor.created_at,
            updated_at=http_monitor.updated_at,
            last_checked_at=http_monitor.last_checked_at,
            last_status_code=http_monitor.last_status_code,
            last_response_time_ms=http_monitor.last_response_time_ms,
            status=http_monitor.status,
            expected_response_time_ms = http_monitor.expected_response_time_ms,
        )

    def to_response_list(
        self,
        http_monitors: list[HTTPMonitorModel],
    ) -> list[HTTP_monitorResponse]:
        return [
            self.to_response(http_monitor)
            for http_monitor in http_monitors
        ]


class HTTP_monitorRepository:
    def __init__(self, engine: AIOEngine):
        self.engine = engine
        self.collection = engine.database[Collections.HTTP_MONITORS]
        self.model = HTTPMonitorModel

    async def create(self, entity: HTTPMonitorModel) -> str:
        document = entity.model_dump()
        document.pop("id", None)

        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_by_id(self, monitor_id: str) -> HTTPMonitorModel | None:
        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return None

        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return HTTPMonitorModel(**document)

    async def get_by_name(self, name: str) -> HTTPMonitorModel | None:
        document = await self.collection.find_one({"name": name})

        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return HTTPMonitorModel(**document)

    async def list_monitors(self) -> list[HTTPMonitorModel]:
        cursor = self.collection.find().sort("created_at", -1)

        monitors = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            monitors.append(HTTPMonitorModel(**document))
        return monitors

    async def update_monitor(self, monitor_id: str, update_data: dict) -> bool:
        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return False

        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one({"_id": object_id}, {"$set": update_data})
        return result.modified_count > 0

    async def delete_monitor(self, monitor_id: str) -> bool:
        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def set_active(self, monitor_id: str, is_active: bool) -> bool:
        return await self.update_monitor(monitor_id, {"is_active": is_active})

    async def get_by_url(self, url: str) -> HTTPMonitorModel | None:
        document = await self.collection.find_one({"url": url})
        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return HTTPMonitorModel(**document)

    async def count_similar_names(self, base_name: str) -> int:
        return await self.collection.count_documents({"name": {"$regex": f"^{base_name}( \\d+)?$"}})

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

    async def count_by_status(self, status: MonitorStatus) -> int:
        return await self.collection.count_documents({"status": status})

    async def get_dashboard_counts(self) -> dict[str, int]:
        total = await self.collection.count_documents({})
        active = await self.collection.count_documents({"is_active": True})
        inactive = await self.collection.count_documents({"is_active": False})
        up = await self.collection.count_documents({"status": MonitorStatus.UP})
        down = await self.collection.count_documents({"status": MonitorStatus.DOWN})
        unknown = await self.collection.count_documents({"status": MonitorStatus.UNKNOWN})

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "up": up,
            "down": down,
            "unknown": unknown,
        }

    async def update_monitor_state(self, monitor_id: str, *, status: MonitorStatus, consecutive_failures: int, consecutive_successes: int, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
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
                    "consecutive_failures": consecutive_failures,
                    "consecutive_successes": consecutive_successes,
                }
            },
        )

        return result.modified_count > 0

    async def count_slow(self) -> int:
        return await self.collection.count_documents(
            {
                "is_slow": True
            }
        )

    async def list_active_monitors(self) -> list[HTTPMonitorModel]:
        cursor = self.collection.find({"is_active": True})
        monitors = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            monitors.append(HTTPMonitorModel(**document))
        return monitors

def get_HTTP_monitor_repository(
    engine: AIOEngine = Depends(get_engine),
) -> HTTP_monitorRepository:
    return HTTP_monitorRepository(engine)
