import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import app.core.scheduler as scheduler_state
from bson import ObjectId
from app.modules.heartbeat_monitor.service import HeartbeatMonitorService
from app.modules.monitor.checkers.heartbeat_checker import HeartbeatChecker
from app.modules.monitor.scheduler import MonitorScheduler
from app.modules.monitor.service import MonitorService
from app.modules.monitor.worker import MonitorWorker
from app.modules.monitor_state.enums import MonitorTransition
from app.modules.monitor_state.service import MonitorStateService
from app.shared.models.base_monitor import MonitorStatus, MonitorType
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


class FakeHeartbeatLookupService:
    def __init__(self, monitor):
        self.monitor = monitor

    async def get_monitor(self, monitor_id):
        return self.monitor


class FailingCheckerFactory:
    def __init__(self):
        self.was_called = False

    def get_checker(self, monitor_type):
        self.was_called = True
        raise AssertionError("An unarmed heartbeat monitor must not be checked.")


def test_monitor_service_does_not_record_or_check_unarmed_heartbeat():
    monitor = make_monitor(last_heartbeat_at=None, status=MonitorStatus.UNKNOWN)
    checker_factory = FailingCheckerFactory()
    heartbeat_service = FakeHeartbeatLookupService(monitor)
    service = MonitorService(
        http_monitor_service=object(),
        api_monitor_service=object(),
        ping_monitor_service=object(),
        heartbeat_monitor_service=heartbeat_service,
        incident_service=object(),
        monitor_result_service=object(),
        monitor_state_service=object(),
        checker_factory=checker_factory,
    )

    asyncio.run(service.check_and_update(monitor))

    assert checker_factory.was_called is False
    assert monitor.status == MonitorStatus.UNKNOWN


class FakeHeartbeatCollection:
    def __init__(self):
        self.monitor = None

    async def insert_one(self, document):
        self.monitor = HeartbeatMonitorModel(**document)
        self.monitor.id = "507f1f77bcf86cd799439011"
        return SimpleNamespace(inserted_id=ObjectId(self.monitor.id))

    async def find_one(self, query):
        if self.monitor is None:
            return None
        if "_id" in query and str(query["_id"]) != self.monitor.id:
            return None
        if (
            "heartbeat_token_hash" in query
            and query["heartbeat_token_hash"] != self.monitor.heartbeat_token_hash
        ):
            return None
        document = self.monitor.model_dump(by_alias=True, exclude={"id"})
        document["_id"] = ObjectId(self.monitor.id)
        return document

    async def update_one(self, query, update):
        if await self.find_one(query) is None:
            return SimpleNamespace(modified_count=0)
        for field, value in update.get("$set", {}).items():
            setattr(self.monitor, field, value)
        for field, value in update.get("$inc", {}).items():
            setattr(self.monitor, field, getattr(self.monitor, field) + value)
        return SimpleNamespace(modified_count=1)


class FakeHeartbeatEngine:
    def __init__(self, collection):
        self.database = {"heartbeat_monitors": collection}


class FakeMonitorService:
    def __init__(self, collection):
        self.collection = collection

    async def process_heartbeat(self, monitor):
        now = datetime.now(timezone.utc)
        self.collection.monitor.status = MonitorStatus.UP
        self.collection.monitor.last_checked_at = now


class FakeScheduler:
    def __init__(self, monitor_service):
        self.monitor_service = monitor_service
        self.started_monitors = []

    async def start_worker(self, monitor):
        self.started_monitors.append(monitor)


def test_service_creates_and_receives_client_heartbeat():
    collection = FakeHeartbeatCollection()
    monitor_service = FakeMonitorService(collection)
    service = HeartbeatMonitorService(
        FakeHeartbeatEngine(collection),
        monitor_service,
    )
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


class FakeMonitorStateCollection:
    def __init__(self):
        self.state = None

    async def find_one(self, query):
        if self.state is None:
            return None
        return self.state.model_dump()

    async def insert_one(self, document):
        self.state = MonitorStateModel(**document)
        return SimpleNamespace(inserted_id=ObjectId())

    async def update_one(self, query, update):
        for field, value in update["$set"].items():
            setattr(self.state, field, value)
        return SimpleNamespace(modified_count=1)


class FakeMonitorStateEngine:
    def __init__(self, collection):
        self.database = {"monitor_states": collection}


def test_heartbeat_state_changes_immediately_on_received_or_missed_beat():
    collection = FakeMonitorStateCollection()
    service = MonitorStateService(FakeMonitorStateEngine(collection))
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
