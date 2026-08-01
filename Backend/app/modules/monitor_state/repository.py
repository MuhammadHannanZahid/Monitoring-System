from datetime import datetime
from app.shared.database_constants import Collections
from app.shared.enums import WebsiteStatus
from app.shared.models.monitor_state import MonitorStateModel

class MonitorStateRepository:
    def __init__(self,database):
        self.collection = database[Collections.MONITOR_STATES]

    async def create(self, website_id: str):
        state = MonitorStateModel(website_id=website_id)
        await self.collection.insert_one(state.model_dump())

        return state

    async def update_state(self, website_id: str, status: WebsiteStatus, failures: int, successes: int, status_code: int | None, response_time_ms: int | None, checked_at: datetime):
        await self.collection.update_one(
            {
                "website_id": website_id
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

    async def get_by_website_id(self, website_id: str) -> MonitorStateModel | None:
        document = await self.collection.find_one({"website_id": website_id})

        if document is None:
            return None

        document.pop("_id", None)
        return MonitorStateModel(**document)
