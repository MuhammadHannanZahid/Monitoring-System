import asyncio
from datetime import datetime, timedelta, timezone

import app.core.scheduler as scheduler_state
from app.modules.heartbeat_monitor.service import HeartbeatMonitorService
from app.modules.monitor.checkers.heartbeat_checker import HeartbeatChecker
from app.modules.monitor.scheduler import MonitorScheduler
from app.modules.monitor.service import MonitorService
from app.modules.monitor.worker import MonitorWorker
from app.modules.monitor_state.enums import MonitorTransition
from app.modules.monitor_state.service import MonitorStateService
from app.shared.enums import MonitorStatus, MonitorType
from app.shared.models.base_monitor import BaseMonitorModel
from app.shared.models.heartbeat_monitor import HeartbeatMonitorModel
from app.shared.models.monitor_state import MonitorStateModel


def make_monitor(**changes) -> HeartbeatMonitorModel:
    now = datetime.now(timezone.utc)
    values = {
        "id": "507f1f77bcf86cd799439011",
        "name": "Client heartbeat",
        "heartbeat_token_hash": "token-hash",
        "expected_heartbeat_interval": 60,
        "grace_period": 10,
        "created_at": now,
        "updated_at": now,
    }
    values.update(changes)
    return HeartbeatMonitorModel(**values)


def test_heartbeat_model_is_standalone_and_loads_legacy_interval_name():
    now = datetime.now(timezone.utc)
    monitor = HeartbeatMonitorModel(
        name="Legacy heartbeat",
        heartbeat_token_hash="token-hash",
        check_interval=30,
        created_at=now,
        updated_at=now,
    )

    assert not isinstance(monitor, BaseMonitorModel)
    assert not hasattr(monitor, "check_interval")
    assert monitor.expected_heartbeat_interval == 30
    assert "check_interval" not in monitor.model_dump()


def test_heartbeat_checker_uses_client_heartbeat_deadline():
    checker = HeartbeatChecker()
    now = datetime.now(timezone.utc)

    on_time = make_monitor(last_heartbeat_at=now - timedelta(seconds=69))
    overdue = make_monitor(last_heartbeat_at=now - timedelta(seconds=71))

    on_time_result = asyncio.run(checker.check(on_time))
    overdue_result = asyncio.run(checker.check(overdue))

    assert on_time_result.status == MonitorStatus.UP
    assert on_time_result.success is True
    assert overdue_result.status == MonitorStatus.DOWN
    assert overdue_result.success is False
    assert overdue_result.response_time_ms is None


def test_heartbeat_worker_waits_for_expected_interval_plus_grace():
    now = datetime.now(timezone.utc)
    monitor = make_monitor(
        last_heartbeat_at=now,
        expected_heartbeat_interval=20,
        grace_period=5,
    )

    remaining = MonitorWorker._seconds_until_heartbeat_deadline(monitor)

    assert 24 <= remaining <= 25


class UnusedMonitorService:
    pass


def test_scheduler_does_not_start_worker_before_first_heartbeat():
    scheduler = MonitorScheduler(UnusedMonitorService())
    monitor = make_monitor(last_heartbeat_at=None)

    asyncio.run(scheduler.start_worker(monitor))

    assert scheduler._workers == {}


class FakeHeartbeatLookupRepository:
    def __init__(self, monitor):
        self.monitor = monitor

    async def get_by_id(self, monitor_id):
        return self.monitor


class FakeRepositoryFactory:
    def __init__(self, monitor):
        self.repository = FakeHeartbeatLookupRepository(monitor)

    def get_repository(self, monitor_type):
        return self.repository


class FailingCheckerFactory:
    def __init__(self):
        self.was_called = False

    def get_checker(self, monitor_type):
        self.was_called = True
        raise AssertionError("An unarmed heartbeat monitor must not be checked.")


def test_monitor_service_does_not_record_or_check_unarmed_heartbeat():
    monitor = make_monitor(last_heartbeat_at=None, status=MonitorStatus.UNKNOWN)
    checker_factory = FailingCheckerFactory()
    service = MonitorService(
        repository_factory=FakeRepositoryFactory(monitor),
        incident_service=object(),
        monitor_result_service=object(),
        monitor_state_service=object(),
        checker_factory=checker_factory,
    )

    asyncio.run(service.check_and_update(monitor))

    assert checker_factory.was_called is False
    assert monitor.status == MonitorStatus.UNKNOWN


class FakeHeartbeatRepository:
    def __init__(self):
        self.monitor = None

    async def create(self, monitor):
        self.monitor = monitor.model_copy(deep=True)
        self.monitor.id = "507f1f77bcf86cd799439011"
        return self.monitor.id

    async def get_by_id(self, monitor_id):
        if self.monitor is None or self.monitor.id != monitor_id:
            return None
        return self.monitor.model_copy(deep=True)

    async def get_by_token_hash(self, token_hash):
        if self.monitor is None or self.monitor.heartbeat_token_hash != token_hash:
            return None
        return self.monitor.model_copy(deep=True)

    async def update_last_heartbeat(self, monitor_id, received_at=None):
        self.monitor.last_heartbeat_at = received_at or datetime.now(timezone.utc)
        self.monitor.heartbeat_count += 1
        return True


class FakeMonitorService:
    def __init__(self, repository):
        self.repository = repository

    async def process_heartbeat(self, monitor):
        now = datetime.now(timezone.utc)
        await self.repository.update_last_heartbeat(monitor.id, now)
        self.repository.monitor.status = MonitorStatus.UP
        self.repository.monitor.last_checked_at = now


class FakeScheduler:
    def __init__(self, monitor_service):
        self.monitor_service = monitor_service
        self.started_monitors = []

    async def start_worker(self, monitor):
        self.started_monitors.append(monitor)


def test_service_creates_and_receives_client_heartbeat():
    repository = FakeHeartbeatRepository()
    monitor_service = FakeMonitorService(repository)
    service = HeartbeatMonitorService(repository, monitor_service)
    fake_scheduler = FakeScheduler(monitor_service)
    previous_scheduler = scheduler_state.scheduler
    scheduler_state.scheduler = fake_scheduler

    try:
        created = asyncio.run(
            service.create_monitor(
                name="Client heartbeat",
                expected_heartbeat_interval=45,
                grace_period=5,
            )
        )
        assert fake_scheduler.started_monitors == []

        received = asyncio.run(service.receive_heartbeat(created.heartbeat_token))
    finally:
        scheduler_state.scheduler = previous_scheduler

    assert created.expected_heartbeat_interval == 45
    assert created.heartbeat_token is not None
    assert received.status == MonitorStatus.UP
    assert received.heartbeat_count == 1
    assert received.last_heartbeat_at is not None
    assert fake_scheduler.started_monitors == [received]


def test_received_heartbeat_timing_log_message_is_reachable():
    received_at = datetime.now(timezone.utc)
    monitor = make_monitor(
        expected_heartbeat_interval=60,
        last_heartbeat_at=received_at - timedelta(seconds=45),
    )

    message = MonitorService._heartbeat_timing_message(monitor, received_at)

    assert message == (
        "beat received 15.00 seconds earlier than the "
        "expected 60-second interval"
    )


class FakeMonitorStateRepository:
    def __init__(self):
        self.state = None

    async def get_by_monitor_id(self, monitor_id, monitor_type):
        return self.state

    async def create(self, monitor_id, monitor_type):
        self.state = MonitorStateModel(
            monitor_id=monitor_id,
            monitor_type=monitor_type,
        )
        return self.state

    async def update_state(
        self,
        monitor_id,
        monitor_type,
        status,
        failures,
        successes,
        status_code,
        response_time_ms,
        checked_at,
    ):
        self.state.status = status
        self.state.consecutive_failures = failures
        self.state.consecutive_successes = successes
        self.state.last_checked_at = checked_at


def test_heartbeat_state_changes_immediately_on_received_or_missed_beat():
    repository = FakeMonitorStateRepository()
    service = MonitorStateService(repository)
    now = datetime.now(timezone.utc)

    up = asyncio.run(
        service.process_result(
            monitor_id="heartbeat-id",
            monitor_type=MonitorType.HEARTBEAT,
            success=True,
            status_code=None,
            response_time_ms=None,
            checked_at=now,
        )
    )
    down = asyncio.run(
        service.process_result(
            monitor_id="heartbeat-id",
            monitor_type=MonitorType.HEARTBEAT,
            success=False,
            status_code=None,
            response_time_ms=None,
            checked_at=now,
        )
    )

    assert up.current_status == MonitorStatus.UP
    assert up.transition == MonitorTransition.UP
    assert down.current_status == MonitorStatus.DOWN
    assert down.transition == MonitorTransition.DOWN
