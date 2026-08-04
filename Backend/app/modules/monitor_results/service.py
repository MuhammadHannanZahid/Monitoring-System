from datetime import datetime, timezone
from app.modules.monitor_results.repository import MonitorResultRepository
from app.shared.models.monitor_result import MonitorResultModel
from app.shared.enums import MonitorStatus

class MonitorResultService:
    def __init__(self, repository: MonitorResultRepository):
        self.repository = repository

    async def record_result(self, monitor_id: str, monitor_type: str, status: MonitorStatus, status_code: int | None, response_time_ms: int | None, success: bool) -> MonitorResultModel:
        result = MonitorResultModel(
            monitor_id=monitor_id,
            monitor_type=monitor_type,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            success=success,
            checked_at=datetime.now(timezone.utc),
        )

        result.id = await self.repository.save_result(result)
        return result

    async def latest_result(self, monitor_id: str) -> MonitorResultModel | None:
        return await self.repository.latest_result(monitor_id)

    async def history(self, monitor_id: str, limit: int = 100) -> list[MonitorResultModel]:
        return await self.repository.list_results(monitor_id, limit)

    async def average_response_time(self, monitor_id: str) -> float:
        return await self.repository.average_response_time(monitor_id)

    async def failure_count(self, monitor_id: str) -> int:
        return await self.repository.count_failures(monitor_id)