from datetime import datetime, timezone, timedelta
from app.core.scheduler import scheduler
from app.modules.heartbeat_monitor.repository import HeartbeatMonitorRepository
from app.shared.enums import MonitorStatus, MonitorType
from app.shared.models.heartbeat_monitor import HeartbeatMonitorModel
import uuid
import hashlib
from app.modules.monitor.service import MonitorService

class HeartbeatMonitorService:
    def __init__(self, repository: HeartbeatMonitorRepository, monitor_service: MonitorService):
        self.repository = repository
        self.monitor_service = monitor_service

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _generate_token(self):
        return uuid.uuid4().hex

    async def create_monitor(self, name: str, check_interval: int, grace_period: int, expected_response_time_ms: int | None, created_by: str | None = None) -> HeartbeatMonitorModel:
        token = self._generate_token()
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)
        monitor = HeartbeatMonitorModel(
            name=name,
            monitor_type=MonitorType.HEARTBEAT,
            heartbeat_token_hash=token_hash,
            check_interval=check_interval,
            grace_period=grace_period,
            expected_response_time_ms=expected_response_time_ms,
            created_by=created_by,
            is_active=True,
            status=MonitorStatus.UNKNOWN,
            last_token_rotated_at=now,
            token_expires_at=now + timedelta(days=90),
            created_at=now,
            updated_at=now,
        )
        monitor.id = await self.repository.create(monitor)
        monitor.heartbeat_token = token
        return monitor

    async def get_monitor(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        return await self.repository.get_by_id(monitor_id)

    async def get_by_token(self, token: str) -> HeartbeatMonitorModel | None:
        token_hash = self._hash_token(token)
        return await self.repository.get_by_token_hash(token_hash)

    async def list_monitors(self) -> list[HeartbeatMonitorModel]:
        return await self.repository.list_monitors()

    async def update_monitor(self, monitor_id: str, name: str | None = None, check_interval: int | None = None, grace_period: int | None = None, expected_response_time_ms: int | None = None) -> HeartbeatMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        if name is not None:
            monitor.name = name
        if check_interval is not None:
            monitor.check_interval = check_interval
        if grace_period is not None:
            monitor.grace_period = grace_period
        if expected_response_time_ms is not None:
            monitor.expected_response_time_ms = expected_response_time_ms
        monitor.updated_at = datetime.now(timezone.utc)
        await self.repository.update(monitor)
        return monitor

    async def delete_monitor(self, monitor_id: str) -> bool:
        if scheduler is not None:
            await scheduler.stop_worker(monitor_id)
        return await self.repository.delete(monitor_id)

    async def activate_monitor(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        await self.repository.set_active(monitor.id, True)
        updated = await self.repository.get_by_id(monitor.id)
        if updated is not None and scheduler is not None:
            await scheduler.start_worker(updated)
        return updated

    async def deactivate_monitor(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        await self.repository.set_active(monitor.id, False)
        if scheduler is not None:
            await scheduler.stop_worker(monitor.id)
        return await self.repository.get_by_id(monitor.id)

    async def regenerate_token(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        new_token = self._generate_token()
        now = datetime.now(timezone.utc)
        monitor.heartbeat_token_hash = self._hash_token(new_token)
        monitor.last_token_rotated_at = now
        monitor.token_expires_at = now + timedelta(days=90)
        monitor.updated_at = now
        await self.repository.update(monitor)
        monitor.heartbeat_token = new_token
        return monitor

    async def receive_heartbeat(self, token: str) -> HeartbeatMonitorModel | None:
        MIN_HEARTBEAT_GAP_SECONDS = 1
        token_hash = self._hash_token(token)
        monitor = await self.repository.get_by_token_hash(token_hash)
        now = datetime.now(timezone.utc)
        if monitor is None:
            return None

        if not monitor.is_active:
            return None

        if (monitor.last_heartbeat_at is not None and (now - monitor.last_heartbeat_at).total_seconds() < MIN_HEARTBEAT_GAP_SECONDS):
            return None

        if monitor.token_expires_at is not None and now > monitor.token_expires_at:
            return None

        await self.monitor_service.process_heartbeat(monitor)
        return await self.repository.get_by_id(monitor.id)