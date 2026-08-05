from datetime import datetime
from app.shared.enums import MonitorType, MonitorStatus
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.modules.API_monitor.repository import API_monitorRepository
from app.shared.models.base_monitor import BaseMonitorModel

class MonitorRepositoryFactory:
    def __init__(self, http_repository: HTTP_monitorRepository, api_repository: API_monitorRepository):
        self.http_repository = http_repository
        self.api_repository = api_repository

        self._repositories = {MonitorType.HTTP: http_repository, MonitorType.API: api_repository}

    def get_repository(self, monitor_type: MonitorType):
        try:
            return self._repositories[monitor_type]

        except KeyError:
            raise ValueError(f"Unsupported monitor type: {monitor_type}")

    async def list_active_monitors(self) -> list[BaseMonitorModel]:
        http_monitors = await self.http_repository.list_monitors()
        api_monitors = await self.api_repository.list_monitors()

        return [
            *(m for m in http_monitors if m.is_active),
            *(m for m in api_monitors if m.is_active),
        ]

    async def update_monitoring_result(self, monitor_type: MonitorType, monitor_id: str, status: MonitorStatus, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
        repository = self.get_repository(monitor_type)

        return await repository.update_monitoring_result(
            monitor_id=monitor_id,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            checked_at=checked_at,
        )