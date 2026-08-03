from datetime import datetime, timezone
from typing import Generic, TypeVar

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        model: type[T],
    ):
        self.collection = collection
        self.model = model

    async def create(self, entity: T) -> str:
        document = entity.model_dump()
        document.pop("id", None)

        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

