from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
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

        refresh_token = self.refresh_token_service.generate_token()
        refresh_token_hash = (self.refresh_token_service.hash_token(refresh_token))

        updated_refresh = await self.repository.update_refresh_token(user.id, refresh_token_hash)
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

    async def create_user(
        self,
        user: UserModel,
    ) -> str:
        document = user.model_dump()
        document.pop("id", None)
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

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
    ):
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            # FIX: Return False to match return type
            return False

        result = await self.collection.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "refresh_token_hash": refresh_token_hash,
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
            # FIX: Return False to match return type
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
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0


def get_auth_repository(
    engine: AIOEngine = Depends(get_engine),
) -> AuthRepository:
    return AuthRepository(engine)
