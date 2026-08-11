from datetime import datetime, timezone
from app.modules.ping_monitor.repository import PingMonitorRepository
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
            await scheduler_state.scheduler.stop_worker(monitor.id)

        await self.repository.delete_monitor(monitor.id)

    async def activate_monitor(self, monitor_id: str) -> PingMonitorModel | None:
        logger.info("Scheduler object: %s", scheduler_state.scheduler)
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        await self.repository.set_active(monitor.id, True)
        updated = await self.repository.get_by_id(monitor.id)
        if updated is not None and scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(updated)
        return updated

    async def deactivate_monitor(self, monitor_id: str) -> PingMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        await self.repository.set_active(monitor.id, False)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor.id)
        return await self.repository.get_by_id(monitor.id)

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


class PingMonitorMapper:
    @staticmethod
    def to_response(monitor: PingMonitorModel) -> PingMonitorResponse:
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

    @staticmethod
    def to_response_list(monitors: list[PingMonitorModel]) -> list[PingMonitorResponse]:
        return [
            PingMonitorMapper.to_response(monitor)
            for monitor in monitors
        ]
