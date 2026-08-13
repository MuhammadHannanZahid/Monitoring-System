from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine
import app.modules.orion_login_manager.orion_token_manager as auth_token_state
from app.service.constants import Collections
from app.service.exceptions import ConflictError, NotFoundError, ValidationError
from app.service.mongo_db.shared_models.db_orion_login_model import AuthProfileModel, AuthProfileResponse, CreateAuthProfileRequest, UpdateAuthProfileRequest

class AuthProfileManager:
    DEPRECATED_FIELDS = {
        "credential_location": "",
        "token_field": "",
        "expires_in_field": "",
    }

    def __init__(self, engine: AIOEngine):
        self.collection = engine.database[Collections.AUTH_PROFILES]

    async def create_profile(self, request: CreateAuthProfileRequest) -> AuthProfileResponse:
        if await self.collection.find_one({"name": request.name}) is not None:
            raise ConflictError("An auth profile with this name already exists.")

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
        return AuthProfileResponse(
            id=profile.id,
            name=profile.name,
            login_url=profile.login_url,
            method=profile.method,
            credential_fields=sorted(profile.credentials),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    async def get_profile_model(self, profile_id: str) -> AuthProfileModel | None:
        try:
            object_id = ObjectId(profile_id)
        except (InvalidId, TypeError):
            return None

        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            return None
        document["id"] = str(document.pop("_id"))
        return AuthProfileModel(**document)

    async def list_profile_models(self) -> list[AuthProfileModel]:
        profiles = []
        async for document in self.collection.find().sort("created_at", -1):
            document["id"] = str(document.pop("_id"))
            profiles.append(AuthProfileModel(**document))
        return profiles

    async def get_profile(self, profile_id: str) -> AuthProfileResponse:
        profile = await self.get_profile_model(profile_id)
        if profile is None:
            raise NotFoundError("Auth profile not found.")
        return AuthProfileResponse(
            id=profile.id,
            name=profile.name,
            login_url=profile.login_url,
            method=profile.method,
            credential_fields=sorted(profile.credentials),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    async def list_profiles(self) -> list[AuthProfileResponse]:
        profiles = await self.list_profile_models()
        return [
            AuthProfileResponse(
                id=profile.id,
                name=profile.name,
                login_url=profile.login_url,
                method=profile.method,
                credential_fields=sorted(profile.credentials),
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
            for profile in profiles
        ]

    async def update_profile(self, profile_id: str, request: UpdateAuthProfileRequest) -> AuthProfileResponse:
        profile = await self.get_profile_model(profile_id)
        if profile is None:
            raise NotFoundError("Auth profile not found.")

        update_data = request.model_dump(exclude_unset=True)
        required_fields = {"name", "login_url", "method", "credentials"}
        invalid_null_fields = [
            field
            for field in required_fields
            if field in update_data and update_data[field] is None
        ]
        if invalid_null_fields:
            raise ValidationError(f"Auth profile fields cannot be null: {', '.join(sorted(invalid_null_fields))}.")
        if update_data.get("headers") is None and "headers" in update_data:
            update_data["headers"] = {}

        if "name" in update_data:
            existing = await self.collection.find_one({"name": update_data["name"]})
            if existing is not None and str(existing["_id"]) != profile_id:
                raise ConflictError("An auth profile with this name already exists.")
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
        updated = await self.get_profile_model(profile_id)
        if updated is None:
            raise NotFoundError("Auth profile not found.")
        return AuthProfileResponse(
            id=updated.id,
            name=updated.name,
            login_url=updated.login_url,
            method=updated.method,
            credential_fields=sorted(updated.credentials),
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    async def delete_profile(self, profile_id: str) -> None:
        try:
            object_id = ObjectId(profile_id)
        except (InvalidId, TypeError):
            raise NotFoundError("Auth profile not found.")

        result = await self.collection.delete_one({"_id": object_id})
        deleted = result.deleted_count > 0
        if not deleted:
            raise NotFoundError("Auth profile not found.")
        self._invalidate_token(profile_id)

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
