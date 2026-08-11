from __future__ import annotations

import os
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.core.security import PasswordService
from app.shared.constants import Collections, Messages
from app.shared.exceptions import ConflictError, NotFoundError, AuthorizationError
from app.shared.models.auth_user import UserModel, UserResponse, UserRole
from app.core.logger import get_logger

logger = get_logger(__name__)

class UserService:
    def __init__(self, repository: UserRepository, password_service: PasswordService):
        self.repository = repository
        self.password_service = password_service

    def _hash_password(self, password: str) -> str:
        return self.password_service.hash_password(password)
    
    async def create_user(self, username: str, password: str, role: UserRole) -> UserModel:
        username_exists = await self.repository.username_exists(username)

        if username_exists:
            raise ConflictError(Messages.USERNAME_ALREADY_EXISTS)

        if role == UserRole.ADMIN:
            logger.warning("Attempted creation of another admin account.")
            raise AuthorizationError(Messages.ADMIN_CREATION_NOT_ALLOWED)

        now = datetime.now(timezone.utc)

        user = UserModel(
            username=username,
            password_hash=self._hash_password(password),
            role=role,
            is_active=True,
            refresh_token_hash=None,
            created_at=now,
            updated_at=now,
            last_login=None,
        )

        user_id = await self.repository.create_user(user)
        created_user = await self.repository.get_by_id(user_id)

        if created_user is None:
            raise RuntimeError("Failed to retrieve newly created user.")

        logger.info("User '%s' created with role '%s'.", created_user.username, created_user.role.value)
        return created_user

    async def get_user(self, user_id: str) -> UserModel:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            logger.warning("Requested user '%s' was not found.", user_id)
            raise NotFoundError(Messages.USER_NOT_FOUND)
        return user

    async def list_users(self) -> list[UserModel]:
        return await self.repository.list_users()

    async def update_user(self, user_id: str, username: str | None = None, password: str | None = None, role: UserRole | None = None, is_active: bool | None = None) -> UserModel:
        user = await self.get_user(user_id)
        update_data: dict[str, object] = {}

        if username is not None:
            if username != user.username:
                exists = await self.repository.username_exists(username)

                if exists:
                    raise ConflictError(Messages.USERNAME_ALREADY_EXISTS)

                if role == UserRole.ADMIN:
                    raise AuthorizationError(Messages.ADMIN_PROMOTION_NOT_ALLOWED)
                update_data["username"] = username

        if password is not None:
            update_data["password_hash"] = self._hash_password(password)

        if role is not None:
            existing_user = await self.repository.get_by_id(user_id)
            if existing_user is None:
                raise NotFoundError(Messages.USER_NOT_FOUND)

            if existing_user.role == UserRole.ADMIN and role != UserRole.ADMIN:
                logger.warning("Attempted role change for admin account '%s'.", existing_user.username)
                raise AuthorizationError(Messages.ADMIN_ROLE_CHANGE_NOT_ALLOWED)

            update_data["role"] = role

        if is_active is not None:
            update_data["is_active"] = is_active

        if update_data:
            await self.repository.update_user(user_id, update_data)

        updated_user = await self.get_user(user_id)
        logger.info("User '%s' updated. Fields changed: %s", updated_user.username, ", ".join(update_data.keys()))
        return updated_user

    async def delete_user(self, user_id: str) -> None:
        user = await self.get_user(user_id)
        if user.role == UserRole.ADMIN:
            logger.warning("Attempted deletion of admin account '%s'.", user.username)
            raise AuthorizationError(Messages.ADMIN_DELETION_NOT_ALLOWED)
        user = await self.get_user(user_id)
        await self.repository.delete_user(user_id)
        logger.info("User '%s' deleted.", user.username)

    async def activate_user(self, user_id: str) -> UserModel:
        user = await self.get_user(user_id)
        await self.repository.set_active(user_id,True)
        logger.info("User '%s' activated.", user.username)
        return await self.get_user(user_id)

    async def deactivate_user(self, user_id: str) -> UserModel:
        user = await self.get_user(user_id)
        if user.role == UserRole.ADMIN:
            logger.warning("Attempted deactivation of admin account '%s'.", user.username)
            raise AuthorizationError(Messages.ADMIN_DEACTIVATION_NOT_ALLOWED)

        user = await self.get_user(user_id)
        await self.repository.set_active(user_id,False)
        logger.info("User '%s' deactivated.", user.username)
        return await self.get_user(user_id)

    def to_response(self, user: UserModel) -> UserResponse:
        return UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
        )

    def to_response_list(self, users: list[UserModel]) -> list[UserResponse]:
        return [self.to_response(user) for user in users]


class UserRepository:
    def __init__(self, engine: AIOEngine):
        self.engine = engine
        self.collection = engine.database[Collections.USERS]

    async def update_seed_admin(self) -> None:
        load_dotenv()
        await self.collection.update_one(
            {"username": os.environ["DEFAULT_ADMIN_USERNAME"]},
            {
                "$set": {
                    "role": UserRole.ADMIN,
                    "is_active": True,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    async def create_user(self, user: UserModel) -> str:
        document = user.model_dump()
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def get_by_id(self, user_id: str) -> UserModel | None:
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return None

        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            return None

        document = dict(document)
        document["id"] = str(document.pop("_id"))
        return UserModel(**document)

    async def get_by_username(self, username: str) -> UserModel | None:
        document = await self.collection.find_one({"username": username})
        if document is None:
            return None

        document = dict(document)
        document["id"] = str(document.pop("_id"))
        return UserModel(**document)

    async def username_exists(self, username: str) -> bool:
        count = await self.collection.count_documents({"username": username}, limit=1)
        return count > 0

    async def list_users(self) -> list[UserModel]:
        cursor = self.collection.find().sort("created_at", -1)
        users = []

        async for document in cursor:
            document["id"] = str(document.pop("_id"))

            users.append(UserModel(**document))
        return users

    async def update_user(self, user_id: str, update_data: dict[str, object]) -> bool:
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return False

        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.update_one({"_id": object_id},{"$set": update_data})
        return result.modified_count > 0

    async def delete_user(self, user_id: str) -> bool:
        try:
            object_id = ObjectId(user_id)

        except InvalidId:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def set_active(self, user_id: str, is_active: bool) -> bool:
        return await self.update_user(user_id,{"is_active": is_active})

def get_user_repository(
    engine: AIOEngine = Depends(get_engine),
) -> UserRepository:
    return UserRepository(engine)
