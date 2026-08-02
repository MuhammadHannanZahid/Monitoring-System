from datetime import datetime
from app.shared.database_constants import Collections
from app.shared.enums import HTTP_monitorStatus
from app.shared.models.monitor_state import MonitorStateModel

class MonitorStateRepository:
    def __init__(self,database):
        self.collection = database[Collections.MONITOR_STATES]

    async def create(self, monitor_id: str):
        state = MonitorStateModel(monitor_id=monitor_id)
        await self.collection.insert_one(state.model_dump())

        return state

    async def update_state(self, monitor_id: str, status: HTTP_monitorStatus, failures: int, successes: int, status_code: int | None, response_time_ms: int | None, checked_at: datetime):
        await self.collection.update_one(
            {
                "monitor_id": monitor_id
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

    async def get_by_monitor_id(self, monitor_id: str) -> MonitorStateModel | None:
        document = await self.collection.find_one({"monitor_id": monitor_id})

        if document is None:
            return None

        document.pop("_id", None)
        return MonitorStateModel(**document)
