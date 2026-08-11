from datetime import datetime
from app.shared.constants import Collections
from app.shared.models.base_monitor import MonitorStatus
from app.shared.models.monitor_state import MonitorStateModel
from app.shared.models.base_monitor import MonitorType

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
