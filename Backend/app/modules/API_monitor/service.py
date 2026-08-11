from datetime import datetime, timezone
from app.shared.models.api_monitor import (
    APIMonitorModel,
    ApiMonitorResponse,
    CreateApiMonitorRequest,
    UpdateApiMonitorRequest,
)
from app.modules.API_monitor.repository import API_monitorRepository
from app.modules.API_monitor.schemas import CreateApiMonitorRequest, UpdateApiMonitorRequest
from app.modules.auth_profiles.repository import AuthProfileRepository
import app.core.scheduler as scheduler_state

class API_monitorService:
    def __init__(
        self,
        repository: API_monitorRepository,
        auth_profile_repository: AuthProfileRepository | None = None,
    ):
        self.repository = repository
        self.auth_profile_repository = auth_profile_repository

    async def create_monitor(self, request: CreateApiMonitorRequest, expected_response_time_ms: int | None = None, created_by: str | None = None) -> APIMonitorModel:

        existing = await self.repository.get_by_name(request.name)
        if existing:
            raise ValueError("API monitor with this name already exists.")

        existing = await self.repository.get_by_url(request.url)
        if existing:
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
        monitor.id = await self.repository.create(monitor)

        # Start scheduler worker immediately
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(monitor)

        return monitor

    async def get_monitor(self, monitor_id: str) -> APIMonitorModel | None:
        return await self.repository.get_by_id(monitor_id)

    async def list_monitors(self) -> list[APIMonitorModel]:
        return await self.repository.list_monitors()

    async def update_monitor(self, monitor_id: str, request: UpdateApiMonitorRequest, expected_response_time_ms: int) -> APIMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None

        update_data = request.model_dump(exclude_unset=True)

        if "name" in update_data:
            existing = await self.repository.get_by_name(update_data["name"])
            if existing and existing.id != monitor_id:
                raise ValueError("API monitor with this name already exists.")

        if "url" in update_data:
            existing = await self.repository.get_by_url(update_data["url"])
            if existing and existing.id != monitor_id:
                raise ValueError("API monitor for this URL already exists.")

        if "auth_profile_id" in update_data:
            await self._validate_auth_profile(update_data["auth_profile_id"])

        success = await self.repository.update_monitor(monitor_id, update_data)

        if not success:
            return None
        return await self.repository.get_by_id(monitor_id)

    async def _validate_auth_profile(self, profile_id: str | None) -> None:
        if profile_id is None:
            return
        if self.auth_profile_repository is None:
            raise ValueError("Auth profile validation is unavailable.")
        if await self.auth_profile_repository.get_by_id(profile_id) is None:
            raise ValueError("Auth profile not found.")

    async def delete_monitor(self, monitor_id: str) -> bool:
        monitor = await self.get_monitor(monitor_id)
        if monitor is None:
            return False
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor_id)
        return await self.repository.delete_monitor(monitor_id)

    async def activate_monitor(self, monitor_id: str):
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        await self.repository.set_active(monitor.id, True)
        updated = await self.repository.get_by_id(monitor.id)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(updated)
        return updated

    async def deactivate_monitor(self, monitor_id: str):
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        await self.repository.set_active(monitor.id, False)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor.id)
        return await self.repository.get_by_id(monitor.id)


class API_monitorMapper:
    @staticmethod
    def to_response(API_monitor: APIMonitorModel) -> ApiMonitorResponse:
        return ApiMonitorResponse(
            id=API_monitor.id,
            name=API_monitor.name,
            url=API_monitor.url,
            method=API_monitor.method,
            headers=API_monitor.headers,
            request_body=API_monitor.request_body,
            expected_status_code=API_monitor.expected_status_code,
            expected_json=API_monitor.expected_json,
            check_interval=API_monitor.check_interval,
            timeout=API_monitor.timeout,
            is_active=API_monitor.is_active,
            created_by=API_monitor.created_by,
            created_at=API_monitor.created_at,
            updated_at=API_monitor.updated_at,
            last_checked_at=API_monitor.last_checked_at,
            last_status_code=API_monitor.last_status_code,
            last_response_time_ms=API_monitor.last_response_time_ms,
            status=API_monitor.status,
            expected_response_time_ms=API_monitor.expected_response_time_ms,
            expected_headers=API_monitor.expected_headers,
            expected_content_type=API_monitor.expected_content_type,
        )

    @staticmethod
    def to_response_list(API_monitors: list[APIMonitorModel]) -> list[ApiMonitorResponse]:
        return [
            API_monitorMapper.to_response(API_monitor)
            for API_monitor in API_monitors
        ]
