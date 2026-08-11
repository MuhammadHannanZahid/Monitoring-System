from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.database_constants import Collections
from app.shared.models.auth_profile import AuthProfileModel


class AuthProfileRepository:
    DEPRECATED_FIELDS = {
        "credential_location": "",
        "token_field": "",
        "expires_in_field": "",
    }

    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database[Collections.AUTH_PROFILES]

    @staticmethod
    def _to_object_id(profile_id: str) -> ObjectId | None:
        try:
            return ObjectId(profile_id)
        except (InvalidId, TypeError):
            return None

    @staticmethod
    def _to_model(document: dict | None) -> AuthProfileModel | None:
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return AuthProfileModel(**document)

    async def create(self, profile: AuthProfileModel) -> str:
        document = profile.model_dump(exclude={"id"})
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_by_id(self, profile_id: str) -> AuthProfileModel | None:
        object_id = self._to_object_id(profile_id)
        if object_id is None:
            return None
        return self._to_model(await self.collection.find_one({"_id": object_id}))

    async def get_by_name(self, name: str) -> AuthProfileModel | None:
        return self._to_model(await self.collection.find_one({"name": name}))

    async def list_profiles(self) -> list[AuthProfileModel]:
        profiles = []
        async for document in self.collection.find().sort("created_at", -1):
            profile = self._to_model(document)
            if profile is not None:
                profiles.append(profile)
        return profiles

    async def update(self, profile_id: str, update_data: dict) -> bool:
        object_id = self._to_object_id(profile_id)
        if object_id is None:
            return False
        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": update_data,
                "$unset": self.DEPRECATED_FIELDS,
            },
        )
        return result.matched_count > 0

    async def delete(self, profile_id: str) -> bool:
        object_id = self._to_object_id(profile_id)
        if object_id is None:
            return False
        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def create_indexes(self) -> None:
        await self.collection.update_many(
            {},
            {"$unset": self.DEPRECATED_FIELDS},
        )
        await self.collection.create_index("name", unique=True)
