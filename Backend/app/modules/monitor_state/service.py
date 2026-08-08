from datetime import datetime
from app.core.config import settings
from app.shared.enums import MonitorStatus
from app.shared.models.monitor_state import MonitorStateModel
from app.modules.monitor_state.schemas import MonitorStateResult
from app.modules.monitor_state.repository import MonitorStateRepository
from app.modules.monitor_state.enums import MonitorTransition
from app.shared.enums import MonitorType

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
