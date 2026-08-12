from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine
import app.modules.monitor.scheduler as scheduler_state
from app.modules.orion_login_manager.service import AuthProfileService
from app.service.constants import Collections
from app.service.mongo_db.shared_models.models.api_monitor import APIMonitorModel, CreateApiMonitorRequest, UpdateApiMonitorRequest
from app.service.mongo_db.shared_models.models.base_monitor import MonitorStatus

class API_monitorService:
    def __init__(self, engine: AIOEngine, auth_profile_service: AuthProfileService | None = None):
        self.collection = engine.database[Collections.API_MONITORS]
        self.auth_profile_service = auth_profile_service

    async def create_monitor(self, request: CreateApiMonitorRequest, expected_response_time_ms: int | None = None, created_by: str | None = None) -> APIMonitorModel:
        if await self.collection.find_one({"name": request.name}) is not None:
            raise ValueError("API monitor with this name already exists.")
        if await self.collection.find_one({"url": request.url}) is not None:
            raise ValueError("API monitor for this URL already exists.")

        await self._validate_auth_profile(request.auth_profile_id)
        now = datetime.now(timezone.utc)
        monitor = APIMonitorModel(
            name=request.name,
            url=request.url,
            method=request.method,
            headers=request.headers,
            request_body=request.request_body,
            expected_status_code=request.expected_status_code,
            expected_response_time_ms=request.expected_response_time_ms,
            expected_json=request.expected_json,
            check_interval=request.check_interval,
            timeout=request.timeout,
            is_active=True,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            last_checked_at=None,
            last_status_code=None,
            last_response_time_ms=None,
            expected_headers=request.expected_headers,
            expected_content_type=request.expected_content_type,
            auth_profile_id=request.auth_profile_id,
        )
        document = monitor.model_dump()
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        monitor.id = str(result.inserted_id)

        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(monitor)
        return monitor

    async def get_monitor(self, monitor_id: str) -> APIMonitorModel | None:
        try:
            object_id = ObjectId(monitor_id)
        except InvalidId:
            return None
        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return APIMonitorModel(**document)

    async def list_monitors(self) -> list[APIMonitorModel]:
        cursor = self.collection.find().sort("created_at", -1)
        monitors = []
        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            monitors.append(APIMonitorModel(**document))
        return monitors

    async def update_monitor(self, monitor_id: str, request: UpdateApiMonitorRequest, expected_response_time_ms: int) -> APIMonitorModel | None:
        monitor = await self.get_monitor(monitor_id)
        if monitor is None:
            return None

        update_data = request.model_dump(exclude_unset=True)
        if "name" in update_data:
            existing = await self.collection.find_one({"name": update_data["name"]})
            if existing is not None and str(existing["_id"]) != monitor_id:
                raise ValueError("API monitor with this name already exists.")
        if "url" in update_data:
            existing = await self.collection.find_one({"url": update_data["url"]})
            if existing is not None and str(existing["_id"]) != monitor_id:
                raise ValueError("API monitor for this URL already exists.")
        if "auth_profile_id" in update_data:
            await self._validate_auth_profile(update_data["auth_profile_id"])

        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": ObjectId(monitor_id)},
            {"$set": update_data},
        )
        if result.matched_count == 0:
            return None
        return await self.get_monitor(monitor_id)

    async def delete_monitor(self, monitor_id: str) -> bool:
        monitor = await self.get_monitor(monitor_id)
        if monitor is None:
            return False
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor_id)
        result = await self.collection.delete_one({"_id": ObjectId(monitor_id)})
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
                    "last_status_code": status_code,
                    "last_response_time_ms": response_time_ms,
                    "last_checked_at": checked_at,
                    "updated_at": checked_at,
                }
            },
        )
        return result.modified_count > 0

    async def _validate_auth_profile(self, profile_id: str | None) -> None:
        if profile_id is None:
            return
        if self.auth_profile_service is None:
            raise ValueError("Auth profile validation is unavailable.")
        if await self.auth_profile_service.get_profile(profile_id) is None:
            raise ValueError("Auth profile not found.")