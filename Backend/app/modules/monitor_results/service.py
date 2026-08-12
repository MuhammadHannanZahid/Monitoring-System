from __future__ import annotations
from datetime import datetime, timedelta, timezone
from odmantic import AIOEngine
from app.shared.constants import Collections
from app.shared.models.base_monitor import MonitorStatus
from app.shared.models.monitor_result import MonitorResultModel

class MonitorResultService:
    def __init__(self, engine: AIOEngine):
        self.collection = engine.database[Collections.MONITOR_RESULTS]

    async def record_result(self, monitor_id: str, monitor_type: str, status: MonitorStatus, status_code: int | None, response_time_ms: int | None, success: bool, is_slow: bool = False) -> MonitorResultModel:
        result = MonitorResultModel(
            monitor_id=monitor_id,
            monitor_type=monitor_type,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            success=success,
            is_slow=is_slow,
            checked_at=datetime.now(timezone.utc),
        )
        document = result.model_dump()
        document.pop("id", None)
        inserted = await self.collection.insert_one(document)
        result.id = str(inserted.inserted_id)
        return result

    async def average_response_time(self) -> float:
        pipeline = [
            {"$match": {"response_time_ms": {"$ne": None}}},
            {"$group": {"_id": None, "avg": {"$avg": "$response_time_ms"}}},
        ]
        result = await self.collection.aggregate(pipeline).to_list(1)
        if not result:
            return 0.0
        return round(result[0]["avg"], 2)

    async def get_recent(self, limit: int = 20) -> list[MonitorResultModel]:
        cursor = self.collection.find().sort("checked_at", -1).limit(limit)
        results = []
        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            results.append(MonitorResultModel(**document))
        return results

    async def get_response_history(self, monitor_id: str, days: int = 7) -> list[MonitorResultModel]:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        cursor = self.collection.find(
            {
                "monitor_id": monitor_id,
                "checked_at": {"$gte": start_date},
            }
        ).sort("checked_at", 1)
        results = []
        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            results.append(MonitorResultModel(**document))
        return results

    async def get_status_history(self, monitor_id: str, days: int = 7) -> list[MonitorResultModel]:
        return await self.get_response_history(monitor_id, days)

    async def get_statistics(self, monitor_id: str, days: int = 7) -> dict[str, int]:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        pipeline = [
            {
                "$match": {
                    "monitor_id": monitor_id,
                    "checked_at": {"$gte": start_date},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "successful": {"$sum": {"$cond": ["$success", 1, 0]}},
                }
            },
        ]
        result = await self.collection.aggregate(pipeline).to_list(1)
        if not result:
            return {"total": 0, "successful": 0}
        return {
            "total": result[0]["total"],
            "successful": result[0]["successful"],
        }

    async def count_slow_checks(self, monitor_id: str) -> int:
        return await self.collection.count_documents(
            {"monitor_id": monitor_id, "is_slow": True}
        )