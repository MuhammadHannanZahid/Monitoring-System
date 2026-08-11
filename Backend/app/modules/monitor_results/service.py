from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.shared.constants import Collections
from app.shared.models.monitor_result import MonitorResultModel
from app.shared.models.base_monitor import MonitorStatus

class MonitorResultService:
    def __init__(self, repository: MonitorResultRepository):
        self.repository = repository

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

        result.id = await self.repository.save_result(result)
        return result

    async def latest_result(self, monitor_id: str) -> MonitorResultModel | None:
        return await self.repository.latest_result(monitor_id)

    async def history(self, monitor_id: str, limit: int = 100) -> list[MonitorResultModel]:
        return await self.repository.list_results(monitor_id, limit)

    async def failure_count(self, monitor_id: str) -> int:
        return await self.repository.count_failures(monitor_id)

    async def slow_check_count(self, monitor_id: str) -> int:
        return await self.repository.count_slow_checks(monitor_id)

    async def average_response_time_for_monitor(self, monitor_id: str) -> float:
        return await self.repository.average_response_time_for_monitor(monitor_id)


class MonitorResultRepository:
    def __init__(self, engine: AIOEngine):
        self.engine = engine
        self.collection = engine.database[Collections.MONITOR_RESULTS]

    async def save_result(self, result: MonitorResultModel) -> str:
        document = result.model_dump()
        document.pop("id", None)
        inserted = await self.collection.insert_one(document)
        return str(inserted.inserted_id)

    async def latest_result(self, monitor_id: str) -> MonitorResultModel | None:
        document = await self.collection.find_one({"monitor_id": monitor_id}, sort=[("checked_at", -1)])

        if document is None:
            return None

        document["id"] = str(document.pop("_id"))
        return MonitorResultModel(**document)

    async def list_results(self, monitor_id: str, limit: int = 100) -> list[MonitorResultModel]:
        cursor = (self.collection.find({"monitor_id": monitor_id}).sort("checked_at", -1).limit(limit))
        results = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            results.append(MonitorResultModel(**document))
        return results

    async def count_failures(self, monitor_id: str) -> int:
        return await self.collection.count_documents(
            {
                "monitor_id": monitor_id,
                "success": False,
            }
        )

    async def average_response_time(self) -> float:
        pipeline = [
            {
                "$match": {
                    "response_time_ms": {"$ne": None}
                }
            },
            {
            "$group": {
                "_id": None,
                "avg": {"$avg": "$response_time_ms"},
                }
            }
        ]

        result = await self.collection.aggregate(pipeline).to_list(1)
        if not result:
            return 0.0
        return round(result[0]["avg"], 2)

    async def get_recent(self, limit: int = 20) -> list[MonitorResultModel]:
        cursor = (self.collection.find().sort("checked_at", -1).limit(limit))
        results = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            results.append(MonitorResultModel(**document))

        return results

    async def get_response_history(self, monitor_id: str, days: int = 7) -> list[MonitorResultModel]:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        cursor = (
            self.collection.find(
                {
                    "monitor_id": monitor_id,
                    "checked_at": {"$gte": start_date},
                }
            )
            .sort("checked_at", 1)
        )

        results = []
        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            results.append(MonitorResultModel(**document))

        return results

    async def get_status_history(self, monitor_id: str, days: int = 7) -> list[MonitorResultModel]:
        return await self.get_response_history(monitor_id=monitor_id, days=days)

    async def get_statistics(self, monitor_id: str, days: int = 7) -> dict[str, int]:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        pipeline = [
            {
                "$match": {
                    "monitor_id": monitor_id,
                    "checked_at": {
                        "$gte": start_date,
                    },
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "successful": {
                        "$sum": {
                            "$cond": ["$success", 1, 0]
                        }
                    },
                }
            },
        ]

        result = await self.collection.aggregate(pipeline).to_list(1)
        if not result:
            return {
                "total": 0,
                "successful": 0,
            }

        return {
            "total": result[0]["total"],
            "successful": result[0]["successful"],
        }

    async def get_today_statistics(self) -> dict[str, float]:
        now = datetime.now(timezone.utc)
        start = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
        pipeline = [
            {
                "$match": {
                    "checked_at": {
                        "$gte": start,
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "checks": {"$sum": 1},
                    "average_response_time": {
                        "$avg": "$response_time_ms"
                    },
                }
            },
        ]

        result = await self.collection.aggregate(pipeline).to_list(1)
        if not result:
            return {
                "checks": 0,
                "average_response_time": 0,
            }

        stats = result[0]
        return {
            "checks": stats["checks"],
            "average_response_time": round(
                stats["average_response_time"] or 0,
                2,
            ),
        }

    async def count_slow_checks(self, monitor_id: str) -> int:
        return await self.collection.count_documents(
            {
                "monitor_id": monitor_id,
                "is_slow": True,
            }
        )

    async def average_response_time_for_monitor(self, monitor_id: str) -> float:
        pipeline = [
            {
                "$match": {
                    "monitor_id": monitor_id,
                    "response_time_ms": {"$ne": None},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "average": {
                        "$avg": "$response_time_ms"
                    }
                }
            }
        ]

        result = await self.collection.aggregate(pipeline).to_list(1)

        if not result:
            return 0.0

        return round(result[0]["average"], 2)

    async def get_statistics_for_all_monitors(self, days: int = 30) -> dict[str, dict[str, int]]:

        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        pipeline = [
            {
                "$match": {
                    "checked_at": {
                        "$gte": start_date
                    }
                }
            },
            {
                "$group": {
                    "_id": "$monitor_id",
                    "total": {
                        "$sum": 1
                    },
                    "successful": {
                        "$sum": {
                            "$cond": [
                                "$success",
                                1,
                                0,
                            ]
                        }
                    }
                }
            }
        ]

        result = await self.collection.aggregate(
            pipeline
        ).to_list(None)

        return {
            row["_id"]: {
                "total": row["total"],
                "successful": row["successful"],
            }
            for row in result
        }

    async def get_latest_result_for_all_monitors(
            self,
    ) -> dict[str, MonitorResultModel]:

        pipeline = [

            {
                "$sort": {
                    "checked_at": -1
                }
            },

            {
                "$group": {

                    "_id": "$monitor_id",

                    "document": {
                        "$first": "$$ROOT"
                    }

                }
            }

        ]

        aggregation = (
            await self.collection
            .aggregate(pipeline)
            .to_list(None)
        )

        results = {}

        for item in aggregation:
            document = item["document"]

            document["id"] = str(
                document.pop("_id")
            )

            results[item["_id"]] = (
                MonitorResultModel(
                    **document
                )
            )

        return results

def get_monitor_result_repository(
    engine: AIOEngine = Depends(get_engine),
) -> MonitorResultRepository:
    return MonitorResultRepository(engine)
