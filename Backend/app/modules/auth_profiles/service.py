from datetime import datetime, timezone

import app.core.auth_tokens as auth_token_state
from app.modules.auth_profiles.repository import AuthProfileRepository
from app.modules.auth_profiles.schemas import (
    AuthProfileResponse,
    CreateAuthProfileRequest,
    UpdateAuthProfileRequest,
)
from app.shared.models.auth_profile import AuthProfileModel


class AuthProfileService:
    def __init__(self, repository: AuthProfileRepository):
        self.repository = repository

    async def create_profile(
        self,
        request: CreateAuthProfileRequest,
    ) -> AuthProfileModel:
        if await self.repository.get_by_name(request.name) is not None:
            raise ValueError("An auth profile with this name already exists.")

        now = datetime.now(timezone.utc)
        profile_data = request.model_dump()
        profile_data["method"] = request.method.upper()
        profile = AuthProfileModel(
            **profile_data,
            created_at=now,
            updated_at=now,
        )
        profile.id = await self.repository.create(profile)
        return profile

    async def get_profile(self, profile_id: str) -> AuthProfileModel | None:
        return await self.repository.get_by_id(profile_id)

    async def list_profiles(self) -> list[AuthProfileModel]:
        return await self.repository.list_profiles()

    async def update_profile(
        self,
        profile_id: str,
        request: UpdateAuthProfileRequest,
    ) -> AuthProfileModel | None:
        profile = await self.repository.get_by_id(profile_id)
        if profile is None:
            return None

        update_data = request.model_dump(exclude_unset=True)
        required_fields = {
            "name",
            "login_url",
            "method",
            "credentials",
        }
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
            existing = await self.repository.get_by_name(update_data["name"])
            if existing is not None and existing.id != profile_id:
                raise ValueError("An auth profile with this name already exists.")
        if "method" in update_data:
            update_data["method"] = update_data["method"].upper()

        await self.repository.update(profile_id, update_data)
        self._invalidate_token(profile_id)
        return await self.repository.get_by_id(profile_id)

    async def delete_profile(self, profile_id: str) -> bool:
        deleted = await self.repository.delete(profile_id)
        if deleted:
            self._invalidate_token(profile_id)
        return deleted

    @staticmethod
    def to_response(profile: AuthProfileModel) -> AuthProfileResponse:
        return AuthProfileResponse(
            id=profile.id,
            name=profile.name,
            login_url=profile.login_url,
            method=profile.method,
            credential_fields=sorted(profile.credentials),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    @staticmethod
    def _invalidate_token(profile_id: str) -> None:
        if auth_token_state.token_manager is not None:
            auth_token_state.token_manager.invalidate(profile_id)
