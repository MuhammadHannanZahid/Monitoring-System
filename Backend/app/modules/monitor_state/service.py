from __future__ import annotations

from datetime import datetime

from app.core.config import settings
from app.shared.constants import Collections
from app.shared.models.base_monitor import MonitorStatus, MonitorType
from app.shared.models.monitor_state import MonitorStateModel
from app.shared.models.monitor_state import MonitorStateResult
from app.modules.monitor_state.enums import MonitorTransition

class MonitorStateService:
    def __init__(self, repository: MonitorStateRepository):
        self.repository = repository

    async def get_or_create(self, monitor_id: str, monitor_type: MonitorType) -> MonitorStateModel:
        state = await self.repository.get_by_monitor_id(monitor_id, monitor_type)
        if state is None:
            await self.repository.create(monitor_id, monitor_type)
            state = await self.repository.get_by_monitor_id(monitor_id, monitor_type)
        return state

    async def process_result(
            self,
            monitor_id: str,
            monitor_type: MonitorType,
            success: bool,
            status_code: int | None,
            response_time_ms: int | None,
            checked_at: datetime,
    ) -> MonitorStateResult:

        state = await self.get_or_create(monitor_id, monitor_type)

        previous_status = state.status

        recovery_threshold = (
            1
            if monitor_type == MonitorType.HEARTBEAT
            else settings.monitor_recovery_threshold
        )
        failure_threshold = (
            1
            if monitor_type == MonitorType.HEARTBEAT
            else settings.monitor_failure_threshold
        )

        if success:
            state.consecutive_successes += 1
            state.consecutive_failures = 0

            if (
                    previous_status != MonitorStatus.UP
                    and state.consecutive_successes >= recovery_threshold
            ):
                state.status = MonitorStatus.UP

        else:
            state.consecutive_failures += 1
            state.consecutive_successes = 0

            if (
                    previous_status != MonitorStatus.DOWN
                    and state.consecutive_failures >= failure_threshold
            ):
                state.status = MonitorStatus.DOWN

        state.last_checked_at = checked_at
        state.last_status_code = status_code
        state.last_response_time_ms = response_time_ms

        await self.save(state)

        transition = MonitorTransition.NONE

        if previous_status != state.status:

            if state.status == MonitorStatus.DOWN:
                transition = MonitorTransition.DOWN

            elif state.status == MonitorStatus.UP:
                transition = MonitorTransition.UP

        return MonitorStateResult(
            state=state,
            previous_status=previous_status,
            current_status=state.status,
            transition=transition,
        )

    async def save(self, state: MonitorStateModel):
        await self.repository.update_state(
            monitor_id=state.monitor_id,
            monitor_type=state.monitor_type,
            status=state.status,
            failures=state.consecutive_failures,
            successes=state.consecutive_successes,
            status_code=state.last_status_code,
            response_time_ms=state.last_response_time_ms,
            checked_at=state.last_checked_at,
        )


class MonitorStateRepository:
    def __init__(self,database):
        self.collection = database[Collections.MONITOR_STATES]

    async def create(self, monitor_id: str, monitor_type: MonitorType):
        state = MonitorStateModel(monitor_id=monitor_id, monitor_type=monitor_type)
        await self.collection.insert_one(state.model_dump())

        return state

    async def update_state(self, monitor_id: str, monitor_type: MonitorType, status: MonitorStatus, failures: int, successes: int, status_code: int | None, response_time_ms: int | None, checked_at: datetime):
        await self.collection.update_one(
            {
                "monitor_id": monitor_id,
                "monitor_type": monitor_type,
            },
            {
                "$set": {
                    "status": status,
                    "consecutive_failures": failures,
                    "consecutive_successes": successes,
                    "last_checked_at": checked_at,
                    "last_status_code": status_code,
                    "last_response_time_ms": response_time_ms,
                }
            }
        )

    async def get_by_monitor_id(self, monitor_id: str, monitor_type: MonitorType) -> MonitorStateModel | None:
        document = await self.collection.find_one(
            {
                "monitor_id": monitor_id,
                "monitor_type": monitor_type,
            }
        )

        if document is None:
            return None

        document.pop("_id", None)
        return MonitorStateModel(**document)
