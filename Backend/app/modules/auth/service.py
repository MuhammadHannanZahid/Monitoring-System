from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from jose import JWTError
from odmantic import AIOEngine

from app.core.database import get_engine
from app.core.jwt import JWTService
from app.core.security import PasswordService, RefreshTokenService
from app.modules.auth.dto import AuthTokens
from app.shared.models.auth_user import UserModel
from app.shared.constants import Collections
from app.shared.exceptions import AuthenticationError, NotFoundError
from app.shared.constants import Messages
from app.core.logger import get_logger

logger = get_logger(__name__)

class AuthService:
    def __init__(self, repository: AuthRepository, password_service: PasswordService, jwt_service: JWTService, refresh_token_service: RefreshTokenService,) -> None:
        self.repository = repository
        self.password_service = password_service
        self.jwt_service = jwt_service
        self.refresh_token_service = refresh_token_service

    async def login(self, username: str, password: str,) -> AuthTokens:
        user = await self.repository.get_by_username(username)

        if user is None or user.id is None:
            logger.warning("Failed login attempt for username '%s'. User does not exist.", username)
            raise AuthenticationError(Messages.INVALID_CREDENTIALS)

        valid_password = self.password_service.verify_password(
            password=password,
            hashed_password=user.password_hash,
        )

        if not valid_password:
            logger.warning("Failed login attempt for username '%s'. Invalid password.", username)
            raise AuthenticationError(Messages.INVALID_CREDENTIALS)

        refresh_token, refresh_token_expires_at = (
            self.jwt_service.create_refresh_token(
                user_id=user.id,
                username=user.username,
                role=user.role,
            )
        )
        refresh_token_hash = self.refresh_token_service.hash_token(refresh_token)

        updated_refresh = await self.repository.update_refresh_token(
            user.id,
            refresh_token_hash,
            refresh_token_expires_at,
        )
        if not updated_refresh:
            raise NotFoundError("User not found.")

        updated_last = await self.repository.update_last_login(user.id)
        if not updated_last:
            raise NotFoundError("User not found.")

        access_token = self.jwt_service.create_access_token(user_id=user.id, username=user.username, role=user.role,)

        logger.info("User '%s' logged in successfully.", user.username)

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_tokens(self, refresh_token: str) -> AuthTokens:
        try:
            payload = self.jwt_service.verify_refresh_token(refresh_token)
        except JWTError as exc:
            raise AuthenticationError(Messages.INVALID_REFRESH_TOKEN) from exc

        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise AuthenticationError(Messages.INVALID_REFRESH_TOKEN)

        user = await self.repository.get_by_id(user_id)
        if (
            user is None
            or user.id is None
            or not user.is_active
            or user.refresh_token_hash is None
            or user.refresh_token_expires_at is None
        ):
            raise AuthenticationError(Messages.INVALID_REFRESH_TOKEN)

        refresh_token_expires_at = user.refresh_token_expires_at
        if refresh_token_expires_at.tzinfo is None:
            refresh_token_expires_at = refresh_token_expires_at.replace(
                tzinfo=timezone.utc
            )
        if refresh_token_expires_at <= datetime.now(timezone.utc):
            raise AuthenticationError(Messages.INVALID_REFRESH_TOKEN)

        if not self.refresh_token_service.verify_token(
            refresh_token,
            user.refresh_token_hash,
        ):
            raise AuthenticationError(Messages.INVALID_REFRESH_TOKEN)

        new_refresh_token, new_refresh_token_expires_at = (
            self.jwt_service.create_refresh_token(
                user_id=user.id,
                username=user.username,
                role=user.role,
            )
        )
        new_refresh_token_hash = self.refresh_token_service.hash_token(
            new_refresh_token
        )
        rotated = await self.repository.rotate_refresh_token(
            user_id=user.id,
            current_refresh_token_hash=user.refresh_token_hash,
            new_refresh_token_hash=new_refresh_token_hash,
            refresh_token_expires_at=new_refresh_token_expires_at,
        )
        if not rotated:
            raise AuthenticationError(Messages.INVALID_REFRESH_TOKEN)

        access_token = self.jwt_service.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
        )
        logger.info("Tokens refreshed for user '%s'.", user.username)
        return AuthTokens(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def get_current_user(self, user_id: str,) -> UserModel:
        user = await self.repository.get_by_id(user_id)

        if user is None:
            logger.warning("Requested current user '%s' was not found.", user_id)
            raise NotFoundError("User not found.")

        return user

    async def logout(self, user_id: str,) -> None:
        updated = await self.repository.clear_refresh_token(user_id)

        if not updated:
            logger.warning("Logout failed. User '%s' not found.", user_id)
            raise NotFoundError(Messages.USER_NOT_FOUND)

        user = await self.repository.get_by_id(user_id)
        if user:
            logger.info("User '%s' logged out.", user.username)


class AuthRepository:
    def __init__(
        self,
        engine: AIOEngine,
    ):
        self.engine = engine
        self.collection = engine.database[Collections.USERS]

    async def get_by_username(
        self,
        username: str,
    ) -> UserModel | None:
        document = await self.collection.find_one({"username": username})

        if not document:
            return None

        document_dict = dict(document)
        document_dict["id"] = str(document_dict.pop("_id"))
        return UserModel(**document_dict)

    async def get_by_id(
        self,
        user_id: str,
    ) -> UserModel | None:
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return None

        document = await self.collection.find_one({"_id": object_id})

        if not document:
            return None

        document_dict = dict(document)
        document_dict["id"] = str(document_dict.pop("_id"))
        return UserModel(**document_dict)

    async def update_refresh_token(
        self,
        user_id: str,
        refresh_token_hash: str,
        refresh_token_expires_at: datetime,
    ) -> bool:
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return False

        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "refresh_token_hash": refresh_token_hash,
                    "refresh_token_expires_at": refresh_token_expires_at,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    async def rotate_refresh_token(
        self,
        user_id: str,
        current_refresh_token_hash: str,
        new_refresh_token_hash: str,
        refresh_token_expires_at: datetime,
    ) -> bool:
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return False

        result = await self.collection.update_one(
            {
                "_id": object_id,
                "refresh_token_hash": current_refresh_token_hash,
            },
            {
                "$set": {
                    "refresh_token_hash": new_refresh_token_hash,
                    "refresh_token_expires_at": refresh_token_expires_at,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    async def update_last_login(
        self,
        user_id: str,
    ):
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return False

        now = datetime.now(timezone.utc)

        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "last_login": now,
                    "updated_at": now,
                }
            },
        )
        return result.modified_count > 0

    async def clear_refresh_token(self, user_id: str) -> bool:
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return False

        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "refresh_token_hash": None,
                    "refresh_token_expires_at": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0


def get_auth_repository(
    engine: AIOEngine = Depends(get_engine),
) -> AuthRepository:
    return AuthRepository(engine)
