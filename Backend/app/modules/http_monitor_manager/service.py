from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine
import app.modules.monitoring_controller.scheduler as scheduler_state
from app.core.logger import get_logger
from app.service.constants import Collections, Messages
from app.service.exceptions import ConflictError, NotFoundError
from app.service.mongo_db.shared_models.db_http_monitor_model import HTTPMonitorModel
from app.service.mongo_db.shared_models.db_monitoring_controller_model import MonitorStatus

logger = get_logger(__name__)

class HTTP_monitorService:
    def __init__(self, engine: AIOEngine):
        self.collection = engine.database[Collections.HTTP_MONITORS]

    async def create_monitor(self, name: str, url: str, check_interval: int, timeout: int, expected_status_code: int, expected_response_time_ms: int) -> HTTPMonitorModel:
        if await self.collection.find_one({"url": url}) is not None:
            logger.warning("Attempted to create HTTP_monitor with existing URL '%s'.", url)
            raise ConflictError(Messages.monitor_ALREADY_EXISTS)

        count = await self.collection.count_documents({"name": {"$regex": f"^{name}( \\d+)?$"}})
        final_name = name
        if count > 0:
            final_name = f"{name} {count}"
            logger.info("HTTP_monitor name '%s' already exists. Assigned new name '%s'.", name, final_name)

        now = datetime.now(timezone.utc)
        monitor = HTTPMonitorModel(
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
        document = monitor.model_dump()
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        monitor.id = str(result.inserted_id)

        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(monitor)
        logger.info("HTTP_monitor '%s' created. URL: %s", monitor.name, monitor.url)
        return monitor

    async def list_monitors(self) -> list[HTTPMonitorModel]:
        cursor = self.collection.find().sort("created_at", -1)
        monitors = []
        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            monitors.append(HTTPMonitorModel(**document))
        return monitors

    async def get_monitor(self, HTTP_monitor_id: str) -> HTTPMonitorModel | None:
        try:
            object_id = ObjectId(HTTP_monitor_id)
        except InvalidId:
            return None
        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return HTTPMonitorModel(**document)

    async def update_monitor(self, HTTP_monitor_id: str, name: str | None, url: str | None, check_interval: int | None, timeout: int | None, expected_status_code: int | None, expected_response_time_ms: int | None, is_active: bool | None = None) -> HTTPMonitorModel:
        monitor = await self.get_monitor(HTTP_monitor_id)
        if monitor is None:
            raise NotFoundError(Messages.monitor_NOT_FOUND)
        update_data = {}

        if name is not None and name != monitor.name:
            count = await self.collection.count_documents({"name": {"$regex": f"^{name}( \\d+)?$"}})
            update_data["name"] = f"{name} {count}" if count > 0 else name
        if url is not None and url != monitor.url:
            existing = await self.collection.find_one({"url": url})
            if existing is not None and str(existing["_id"]) != HTTP_monitor_id:
                logger.warning("Attempted to update HTTP_monitor '%s' with existing URL '%s'.", monitor.name, url)
                raise ConflictError(Messages.monitor_ALREADY_EXISTS)
            update_data["url"] = url
        if check_interval is not None and check_interval != monitor.check_interval:
            update_data["check_interval"] = check_interval
        if timeout is not None and timeout != monitor.timeout:
            update_data["timeout"] = timeout
        if expected_status_code is not None and expected_status_code != monitor.expected_status_code:
            update_data["expected_status_code"] = expected_status_code
        if expected_response_time_ms is not None and expected_response_time_ms != monitor.expected_response_time_ms:
            update_data["expected_response_time_ms"] = expected_response_time_ms
        if is_active is not None and is_active != monitor.is_active:
            update_data["is_active"] = is_active

        if not update_data:
            return monitor

        update_data["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": ObjectId(HTTP_monitor_id)},
            {"$set": update_data},
        )
        updated_monitor = await self.get_monitor(HTTP_monitor_id)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(updated_monitor.id)
            if updated_monitor.is_active:
                await scheduler_state.scheduler.start_worker(updated_monitor)
        logger.info("HTTP_monitor '%s' updated. Fields changed: %s", updated_monitor.name, ", ".join(update_data.keys()))
        return updated_monitor

    async def delete_monitor(self, HTTP_monitor_id: str) -> None:
        monitor = await self.get_monitor(HTTP_monitor_id)
        if monitor is None:
            raise NotFoundError(Messages.monitor_NOT_FOUND)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor.id)
        await self.collection.delete_one({"_id": ObjectId(monitor.id)})
        logger.info("HTTP_monitor '%s' deleted.", monitor.name)

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
