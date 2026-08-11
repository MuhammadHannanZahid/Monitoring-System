from datetime import datetime, timezone, timedelta
import hashlib
import uuid

import app.core.scheduler as scheduler_state
from app.modules.heartbeat_monitor.repository import HeartbeatMonitorRepository
from app.shared.models.base_monitor import MonitorStatus, MonitorType
from app.shared.models.heartbeat_monitor import (
    HeartbeatMonitorModel,
    HeartbeatMonitorResponse,
    HeartbeatTokenResponse,
    RegenerateHeartbeatTokenResponse,
)
from app.modules.monitor.service import MonitorService


class HeartbeatMonitorService:
    def __init__(
        self,
        repository: HeartbeatMonitorRepository,
        monitor_service: MonitorService | None = None,
    ):
        self.repository = repository
        self.monitor_service = monitor_service

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _generate_token(self) -> str:
        return uuid.uuid4().hex

    def _get_monitor_service(self) -> MonitorService:
        if self.monitor_service is not None:
            return self.monitor_service
        if scheduler_state.scheduler is None:
            raise RuntimeError("The monitor scheduler has not been initialized.")
        return scheduler_state.scheduler.monitor_service

    async def create_monitor(
        self,
        name: str,
        expected_heartbeat_interval: int,
        grace_period: int,
        created_by: str | None = None,
    ) -> HeartbeatMonitorModel:
        token = self._generate_token()
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)
        monitor = HeartbeatMonitorModel(
            name=name,
            monitor_type=MonitorType.HEARTBEAT,
            heartbeat_token_hash=token_hash,
            expected_heartbeat_interval=expected_heartbeat_interval,
            grace_period=grace_period,
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

    async def update_monitor(
        self,
        monitor_id: str,
        name: str | None = None,
        expected_heartbeat_interval: int | None = None,
        grace_period: int | None = None,
    ) -> HeartbeatMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        if name is not None:
            monitor.name = name
        if expected_heartbeat_interval is not None:
            monitor.expected_heartbeat_interval = expected_heartbeat_interval
        if grace_period is not None:
            monitor.grace_period = grace_period
        monitor.updated_at = datetime.now(timezone.utc)
        await self.repository.update(monitor)
        updated = await self.repository.get_by_id(monitor_id)
        if (
            updated is not None
            and updated.is_active
            and updated.last_heartbeat_at is not None
            and scheduler_state.scheduler is not None
        ):
            await scheduler_state.scheduler.stop_worker(monitor_id)
            await scheduler_state.scheduler.start_worker(updated)
        return updated

    async def delete_monitor(self, monitor_id: str) -> bool:
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor_id)
        return await self.repository.delete(monitor_id)

    async def activate_monitor(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        await self.repository.set_active(monitor.id, True)
        updated = await self.repository.get_by_id(monitor.id)
        if (
            updated is not None
            and updated.last_heartbeat_at is not None
            and scheduler_state.scheduler is not None
        ):
            await scheduler_state.scheduler.start_worker(updated)
        return updated

    async def deactivate_monitor(self, monitor_id: str) -> HeartbeatMonitorModel | None:
        monitor = await self.repository.get_by_id(monitor_id)
        if monitor is None:
            return None
        await self.repository.set_active(monitor.id, False)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor.id)
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
        token_hash = self._hash_token(token)
        monitor = await self.repository.get_by_token_hash(token_hash)
        now = datetime.now(timezone.utc)
        if monitor is None:
            return None

        if not monitor.is_active:
            return None

        if monitor.token_expires_at is not None and now > monitor.token_expires_at:
            return None

        await self._get_monitor_service().process_heartbeat(monitor)
        updated = await self.repository.get_by_id(monitor.id)
        if updated is not None and scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(updated)
        return updated


class HeartbeatMonitorMapper:

    @staticmethod
    def to_response(
        monitor: HeartbeatMonitorModel,
    ) -> HeartbeatMonitorResponse:
        return HeartbeatMonitorResponse(
            id=monitor.id,
            name=monitor.name,
            expected_heartbeat_interval=monitor.expected_heartbeat_interval,
            grace_period=monitor.grace_period,
            status=monitor.status.value,
            is_active=monitor.is_active,
            last_heartbeat_at=(
                monitor.last_heartbeat_at.isoformat()
                if monitor.last_heartbeat_at
                else None
            ),
            created_at=monitor.created_at.isoformat(),
            updated_at=monitor.updated_at.isoformat(),
        )

    @staticmethod
    def to_response_list(
        monitors: list[HeartbeatMonitorModel],
    ) -> list[HeartbeatMonitorResponse]:
        return [
            HeartbeatMonitorMapper.to_response(m)
            for m in monitors
        ]

    @staticmethod
    def to_token_response(
        monitor: HeartbeatMonitorModel,
    ) -> HeartbeatTokenResponse:
        return HeartbeatTokenResponse(
            heartbeat_token=monitor.heartbeat_token,
        )

    @staticmethod
    def to_regenerated_token_response(
        monitor: HeartbeatMonitorModel,
    ) -> RegenerateHeartbeatTokenResponse:
        return RegenerateHeartbeatTokenResponse(
            heartbeat_token=monitor.heartbeat_token,
        )
