from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine

import app.modules.auth_profiles.token_manager as auth_token_state
from app.shared.constants import Collections
from app.shared.models.auth_profile import (
    AuthProfileModel,
    CreateAuthProfileRequest,
    UpdateAuthProfileRequest,
)


class AuthProfileService:
    DEPRECATED_FIELDS = {
        "credential_location": "",
        "token_field": "",
        "expires_in_field": "",
    }

    def __init__(self, engine: AIOEngine):
        self.collection = engine.database[Collections.AUTH_PROFILES]

    async def create_profile(
        self,
        request: CreateAuthProfileRequest,
    ) -> AuthProfileModel:
        if await self.collection.find_one({"name": request.name}) is not None:
            raise ValueError("An auth profile with this name already exists.")

        now = datetime.now(timezone.utc)
        profile_data = request.model_dump()
        profile_data["method"] = request.method.upper()
        profile = AuthProfileModel(
            **profile_data,
            created_at=now,
            updated_at=now,
        )
        document = profile.model_dump(exclude={"id"})
        result = await self.collection.insert_one(document)
        profile.id = str(result.inserted_id)
        return profile

    async def get_profile(self, profile_id: str) -> AuthProfileModel | None:
        try:
            object_id = ObjectId(profile_id)
        except (InvalidId, TypeError):
            return None

        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return AuthProfileModel(**document)

    async def list_profiles(self) -> list[AuthProfileModel]:
        profiles = []
        async for document in self.collection.find().sort("created_at", -1):
            document["id"] = str(document.pop("_id"))
            profiles.append(AuthProfileModel(**document))
        return profiles

    async def update_profile(
        self,
        profile_id: str,
        request: UpdateAuthProfileRequest,
    ) -> AuthProfileModel | None:
        profile = await self.get_profile(profile_id)
        if profile is None:
            return None

        update_data = request.model_dump(exclude_unset=True)
        required_fields = {"name", "login_url", "method", "credentials"}
        invalid_null_fields = [
            field
            for field in required_fields
            if field in update_data and update_data[field] is None
        ]
        if invalid_null_fields:
            raise ValueError(
                f"Auth profile fields cannot be null: {', '.join(sorted(invalid_null_fields))}."
            )
        if update_data.get("headers") is None and "headers" in update_data:
            update_data["headers"] = {}

        if "name" in update_data:
            existing = await self.collection.find_one({"name": update_data["name"]})
            if existing is not None and str(existing["_id"]) != profile_id:
                raise ValueError("An auth profile with this name already exists.")
        if "method" in update_data:
            update_data["method"] = update_data["method"].upper()

        update_data["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$set": update_data,
                "$unset": self.DEPRECATED_FIELDS,
            },
        )
        self._invalidate_token(profile_id)
        return await self.get_profile(profile_id)

    async def delete_profile(self, profile_id: str) -> bool:
        try:
            object_id = ObjectId(profile_id)
        except (InvalidId, TypeError):
            return False

        result = await self.collection.delete_one({"_id": object_id})
        deleted = result.deleted_count > 0
        if deleted:
            self._invalidate_token(profile_id)
        return deleted

    async def create_indexes(self) -> None:
        await self.collection.update_many(
            {},
            {"$unset": self.DEPRECATED_FIELDS},
        )
        await self.collection.create_index("name", unique=True)

    @staticmethod
    def _invalidate_token(profile_id: str) -> None:
        if auth_token_state.token_manager is not None:
            auth_token_state.token_manager.invalidate(profile_id)
