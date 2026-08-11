from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.shared.models.base_monitor import MonitorStatus, MonitorType
from app.shared.models.base_monitor import BaseMonitorModel
from app.shared.models.heartbeat_monitor import HeartbeatMonitorModel

if TYPE_CHECKING:
    from app.modules.API_monitor.service import API_monitorRepository
    from app.modules.HTTP_monitor.service import HTTP_monitorRepository
    from app.modules.heartbeat_monitor.service import HeartbeatMonitorRepository
    from app.modules.ping_monitor.service import PingMonitorRepository

MonitorModel = BaseMonitorModel | HeartbeatMonitorModel


class MonitorRepositoryFactory:
    def __init__(self, http_repository: HTTP_monitorRepository, api_repository: API_monitorRepository, ping_repository: PingMonitorRepository, heartbeat_repository: HeartbeatMonitorRepository):
        self.http_repository = http_repository
        self.api_repository = api_repository
        self.ping_repository = ping_repository
        self.heartbeat_repository = heartbeat_repository

        self._repositories = {
            MonitorType.HTTP: http_repository,
            MonitorType.API: api_repository,
            MonitorType.PING: ping_repository,
            MonitorType.HEARTBEAT: heartbeat_repository,
        }

    def get_repository(self, monitor_type: MonitorType):
        try:
            return self._repositories[monitor_type]

        except KeyError:
            raise ValueError(f"Unsupported monitor type: {monitor_type}")

    async def list_active_monitors(self) -> list[MonitorModel]:
        http_monitors = await self.http_repository.list_active_monitors()
        api_monitors = await self.api_repository.list_active_monitors()
        ping_monitors = await self.ping_repository.list_active_monitors()
        heartbeat_monitors = await self.heartbeat_repository.list_active_monitors()

        return [*http_monitors, *api_monitors, *ping_monitors, *heartbeat_monitors]

    async def update_monitoring_result(self, monitor_type: MonitorType, monitor_id: str, status: MonitorStatus, status_code: int | None, response_time_ms: int | None, checked_at: datetime) -> bool:
        repository = self.get_repository(monitor_type)

        return await repository.update_monitoring_result(
            monitor_id=monitor_id,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            checked_at=checked_at,
        )

    async def list_monitors(self) -> list[MonitorModel]:
        http_monitors = await self.http_repository.list_monitors()
        api_monitors = await self.api_repository.list_monitors()
        ping_monitors = await self.ping_repository.list_monitors()
        heartbeat_monitors = await self.heartbeat_repository.list_monitors()

        return [*http_monitors, *api_monitors, *ping_monitors, *heartbeat_monitors]

    async def get_monitor(self, monitor_id: str) -> MonitorModel | None:
        for repository in self._repositories.values():
            monitor = await repository.get_by_id(monitor_id)
            if monitor is not None:
                return monitor
        return None
