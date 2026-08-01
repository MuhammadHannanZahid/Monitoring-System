from datetime import datetime
from app.core.config import settings
from app.shared.enums import WebsiteStatus
from app.shared.models.monitor_state import MonitorStateModel
from app.modules.monitor_state.schemas import MonitorStateResult
from app.modules.monitor_state.repository import MonitorStateRepository
from app.modules.monitor_state.enums import MonitorTransition

class MonitorStateService:
    def __init__(self, repository: MonitorStateRepository):
        self.repository = repository

    async def get_or_create(self, website_id: str) -> MonitorStateModel:
        state = await self.repository.get_by_website_id(website_id)
        if state is None:
            await self.repository.create(website_id)
            state = await self.repository.get_by_website_id(website_id)
        return state

    async def process_result(
            self,
            website_id: str,
            success: bool,
            status_code: int | None,
            response_time_ms: int | None,
            checked_at: datetime,
    ) -> MonitorStateResult:

        state = await self.get_or_create(website_id)

        previous_status = state.status

        if success:
            state.consecutive_successes += 1
            state.consecutive_failures = 0

            if (
                    previous_status != WebsiteStatus.UP
                    and state.consecutive_successes >= settings.monitor_recovery_threshold
            ):
                state.status = WebsiteStatus.UP

        else:
            state.consecutive_failures += 1
            state.consecutive_successes = 0

            if (
                    previous_status != WebsiteStatus.DOWN
                    and state.consecutive_failures >= settings.monitor_failure_threshold
            ):
                state.status = WebsiteStatus.DOWN

        state.last_checked_at = checked_at
        state.last_status_code = status_code
        state.last_response_time_ms = response_time_ms

        await self.save(state)

        transition = MonitorTransition.NONE

        if previous_status != state.status:

            if state.status == WebsiteStatus.DOWN:
                transition = MonitorTransition.DOWN

            elif state.status == WebsiteStatus.UP:
                transition = MonitorTransition.UP

        return MonitorStateResult(
            state=state,
            previous_status=previous_status,
            current_status=state.status,
            transition=transition,
        )

    async def save(self, state: MonitorStateModel):
        await self.repository.update_state(
            website_id=state.website_id,
            status=state.status,
            failures=state.consecutive_failures,
            successes=state.consecutive_successes,
            status_code=state.last_status_code,
            response_time_ms=state.last_response_time_ms,
            checked_at=state.last_checked_at,
        )