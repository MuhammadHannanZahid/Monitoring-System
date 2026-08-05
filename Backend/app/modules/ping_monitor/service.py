from datetime import datetime, timezone
from app.modules.ping_monitor.repository import PingMonitorRepository
from app.shared.enums import MonitorStatus, MonitorType
from app.shared.models.ping_monitor import PingMonitorModel

class PingMonitorService:
    def __init__(self, repository: PingMonitorRepository):
        self.repository = repository

    async def create_monitor(self, name: str, host: str, check_interval: int, timeout: int, expected_response_time_ms: int | None, created_by: str | None = None) -> PingMonitorModel:
        monitor = PingMonitorModel(
            name=name,
            host=host,
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
            monitor.host = host

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
        return await self.repository.delete(monitor_id)

    async def activate_monitor(self, monitor_id: str) -> PingMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None

        monitor.is_active = True
        monitor.updated_at = datetime.now(timezone.utc)
        await self.repository.update(monitor)
        return monitor

    async def deactivate_monitor(self, monitor_id: str) -> PingMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None

        monitor.is_active = False
        monitor.updated_at = datetime.now(timezone.utc)
        await self.repository.update(monitor)
        return monitor