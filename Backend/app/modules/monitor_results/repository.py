from datetime import datetime
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.shared.database_constants import Collections
from app.shared.models.monitor_result import MonitorResultModel

class MonitorResultRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database[Collections.MONITOR_RESULTS]

    async def save_result(self, result: MonitorResultModel) -> str:
        document = result.model_dump()
        document.pop("id", None)
        inserted = await self.collection.insert_one(document)
        return str(inserted.inserted_id)

    async def latest_result(self, website_id: str) -> MonitorResultModel | None:
        document = await self.collection.find_one({"website_id": website_id}, sort=[("checked_at", -1)])

        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return MonitorResultModel(**document)

    async def list_results(self, website_id: str, limit: int = 100) -> list[MonitorResultModel]:
        cursor = (self.collection.find({"website_id": website_id}).sort("checked_at", -1).limit(limit))
        results = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            results.append(MonitorResultModel(**document))
        return results

    async def average_response_time(self, website_id: str) -> float:
        pipeline = [
            {
                "$match": {
                    "website_id": website_id,
                    "response_time_ms": {"$ne": None},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "average": {
                        "$avg": "$response_time_ms"
                    },
                }
            },
        ]

        data = await self.collection.aggregate(pipeline).to_list(1)

        if not data:
            return 0.0
        return float(data[0]["average"])

    async def count_failures(self, website_id: str) -> int:
        return await self.collection.count_documents(
            {
                "website_id": website_id,
                "success": False,
            }
        )

    async def average_response_time(self) -> float:
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg": {
                        "$avg": "$response_time_ms"
                    },
                }
            }
        ]

        result = await self.collection.aggregate(pipeline).to_list(1)

        if not result:
            return 0.0

        return round(result[0]["avg"], 2)

def get_monitor_result_repository(database: AsyncIOMotorDatabase = Depends(get_database)) -> MonitorResultRepository:
    return MonitorResultRepository(database)