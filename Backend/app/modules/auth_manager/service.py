from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from jose import JWTError
from odmantic import AIOEngine
from app.core.jwt import JWTService
from app.core.logger import get_logger
from app.core.security import PasswordService, RefreshTokenService
from app.service.constants import Collections, Messages
from app.service.exceptions import AuthenticationError, NotFoundError
from app.service.mongo_db.shared_models.db_user_account_model import AuthTokens, UserModel

logger = get_logger(__name__)

class AuthService:
    def __init__(self, engine: AIOEngine, password_service: PasswordService, jwt_service: JWTService, refresh_token_service: RefreshTokenService) -> None:
        self.collection = engine.database[Collections.USERS]
        self.password_service = password_service
        self.jwt_service = jwt_service
        self.refresh_token_service = refresh_token_service

    async def login(self, username: str, password: str) -> AuthTokens:
        document = await self.collection.find_one({"username": username})
        if document is None:
            logger.warning("Failed login attempt for username '%s'. User does not exist.", username)
            raise AuthenticationError(Messages.INVALID_CREDENTIALS)

        document["id"] = str(document.pop("_id"))
        user = UserModel(**document)
        if user.id is None or not self.password_service.verify_password(
            password=password,
            hashed_password=user.password_hash):
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
        now = datetime.now(timezone.utc)
        updated = await self.collection.update_one(
            {"_id": ObjectId(user.id)},
            {
                "$set": {
                    "refresh_token_hash": refresh_token_hash,
                    "refresh_token_expires_at": refresh_token_expires_at,
                    "last_login": now,
                    "updated_at": now,
                }
            },
        )
        if updated.matched_count == 0:
            raise NotFoundError(Messages.USER_NOT_FOUND)

        access_token = self.jwt_service.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
        )
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
        try:
            object_id = ObjectId(user_id)
        except InvalidId as exc:
            raise AuthenticationError(Messages.INVALID_REFRESH_TOKEN) from exc

        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            raise AuthenticationError(Messages.INVALID_REFRESH_TOKEN)
        document["id"] = str(document.pop("_id"))
        user = UserModel(**document)
        if user.id is None or not user.is_active or user.refresh_token_hash is None or user.refresh_token_expires_at is None:
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
        rotated = await self.collection.update_one(
            {
                "_id": object_id,
                "refresh_token_hash": user.refresh_token_hash,
            },
            {
                "$set": {
                    "refresh_token_hash": new_refresh_token_hash,
                    "refresh_token_expires_at": new_refresh_token_expires_at,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        if rotated.modified_count == 0:
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

    async def get_current_user(self, user_id: str) -> UserModel:
        try:
            object_id = ObjectId(user_id)
        except InvalidId as exc:
            raise NotFoundError(Messages.USER_NOT_FOUND) from exc

        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            logger.warning("Requested current user '%s' was not found.", user_id)
            raise NotFoundError(Messages.USER_NOT_FOUND)
        document["id"] = str(document.pop("_id"))
        return UserModel(**document)

    async def logout(self, user_id: str) -> None:
        try:
            object_id = ObjectId(user_id)
        except InvalidId as exc:
            raise NotFoundError(Messages.USER_NOT_FOUND) from exc

        document = await self.collection.find_one({"_id": object_id})
        if document is None:
            logger.warning("Logout failed. User '%s' not found.", user_id)
            raise NotFoundError(Messages.USER_NOT_FOUND)

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
        if result.matched_count == 0:
            raise NotFoundError(Messages.USER_NOT_FOUND)
        logger.info("User '%s' logged out.", document["username"])
