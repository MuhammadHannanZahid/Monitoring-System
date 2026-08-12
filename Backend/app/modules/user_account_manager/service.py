from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from odmantic import AIOEngine
from app.core.logger import get_logger
from app.core.security import PasswordService
from app.service.constants import Collections, Messages
from app.service.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.service.mongo_db.shared_models.db_user_account_model import UserModel, UserRole

logger = get_logger(__name__)

class UserService:
    def __init__(self, engine: AIOEngine, password_service: PasswordService):
        self.collection = engine.database[Collections.USERS]
        self.password_service = password_service

    async def create_user(self, username: str, password: str, role: UserRole) -> UserModel:
        if await self.collection.find_one({"username": username}) is not None:
            raise ConflictError(Messages.USERNAME_ALREADY_EXISTS)
        if role == UserRole.ADMIN:
            logger.warning("Attempted creation of another admin account.")
            raise AuthorizationError(Messages.ADMIN_CREATION_NOT_ALLOWED)

        now = datetime.now(timezone.utc)
        user = UserModel(
            username=username,
            password_hash=self.password_service.hash_password(password),
            role=role,
            is_active=True,
            refresh_token_hash=None,
            created_at=now,
            updated_at=now,
            last_login=None,
        )
        document = user.model_dump()
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        user.id = str(result.inserted_id)
        logger.info("User '%s' created with role '%s'.", user.username, user.role.value)
        return user

    async def get_user(self, user_id: str) -> UserModel:
        try:
            object_id = ObjectId(user_id)
        except InvalidId as exc:
            raise NotFoundError(Messages.USER_NOT_FOUND) from exc

        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            logger.warning("Requested user '%s' was not found.", user_id)
            raise NotFoundError(Messages.USER_NOT_FOUND)
        document["id"] = str(document.pop("_id"))
        return UserModel(**document)

    async def list_users(self) -> list[UserModel]:
        cursor = self.collection.find().sort("created_at", -1)
        users = []
        async for document in cursor:
            document["id"] = str(document.pop("_id"))
            users.append(UserModel(**document))
        return users

    async def update_user(self, user_id: str, username: str | None = None, password: str | None = None, role: UserRole | None = None, is_active: bool | None = None) -> UserModel:
        user = await self.get_user(user_id)
        update_data: dict[str, object] = {}

        if username is not None and username != user.username:
            existing = await self.collection.find_one({"username": username})
            if existing is not None:
                raise ConflictError(Messages.USERNAME_ALREADY_EXISTS)
            if role == UserRole.ADMIN:
                raise AuthorizationError(Messages.ADMIN_PROMOTION_NOT_ALLOWED)
            update_data["username"] = username

        if password is not None:
            update_data["password_hash"] = self.password_service.hash_password(password)

        if role is not None:
            if user.role == UserRole.ADMIN and role != UserRole.ADMIN:
                logger.warning("Attempted role change for admin account '%s'.", user.username)
                raise AuthorizationError(Messages.ADMIN_ROLE_CHANGE_NOT_ALLOWED)
            update_data["role"] = role

        if is_active is not None:
            update_data["is_active"] = is_active

        if update_data:
            update_data["updated_at"] = datetime.now(timezone.utc)
            await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )

        updated_user = await self.get_user(user_id)
        logger.info("User '%s' updated. Fields changed: %s", updated_user.username, ", ".join(update_data.keys()))
        return updated_user

    async def delete_user(self, user_id: str) -> None:
        user = await self.get_user(user_id)
        if user.role == UserRole.ADMIN:
            logger.warning("Attempted deletion of admin account '%s'.", user.username)
            raise AuthorizationError(Messages.ADMIN_DELETION_NOT_ALLOWED)
        await self.collection.delete_one({"_id": ObjectId(user_id)})
        logger.info("User '%s' deleted.", user.username)

    async def ensure_default_admin(self, username: str, password: str) -> bool:
        now = datetime.now(timezone.utc)
        existing = await self.collection.find_one({"username": username})
        if existing is not None:
            await self.collection.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "role": UserRole.ADMIN,
                        "is_active": True,
                        "updated_at": now,
                    }
                },
            )
            return False

        admin = UserModel(
            username=username,
            password_hash=self.password_service.hash_password(password),
            role=UserRole.ADMIN,
            refresh_token_hash=None,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_login=None,
        )
        document = admin.model_dump()
        document.pop("id", None)
        await self.collection.insert_one(document)
        return True