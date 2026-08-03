from datetime import datetime, timezone
from app.shared.models.api_monitor import APIMonitorModel
from app.modules.API_monitor.repository import API_monitorRepository
from app.modules.API_monitor.schemas import CreateApiMonitorRequest, UpdateApiMonitorRequest

class API_monitorService:
    def __init__(self, repository: API_monitorRepository):
        self.repository = repository

    async def create_monitor(self, request: CreateApiMonitorRequest, created_by: str | None = None) -> APIMonitorModel:

        existing = await self.repository.get_by_name(request.name)
        if existing:
            raise ValueError("API monitor with this name already exists.")

        existing = await self.repository.get_by_url(request.url)
        if existing:
            raise ValueError("API monitor for this URL already exists.")

        now = datetime.now(timezone.utc)

        monitor = APIMonitorModel(
            name=request.name,
            url=request.url,
            method=request.method,
            headers=request.headers,
            request_body=request.request_body,
            expected_status_code=request.expected_status_code,
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
        )
        monitor.id = await self.repository.create(monitor)
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

        success = await self.repository.update_monitor(monitor_id, update_data)

        if not success:
            return None
        return await self.repository.get_by_id(monitor_id)

    async def delete_monitor(self, monitor_id: str) -> bool:
        return await self.repository.delete_monitor(monitor_id)

    async def activate_monitor(self, monitor_id: str) -> bool:
        return await self.repository.set_active(monitor_id, True)

    async def deactivate_monitor(self, monitor_id: str) -> bool:
        return await self.repository.set_active(monitor_id, False)