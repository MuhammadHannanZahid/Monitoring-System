from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.shared.constants import Collections
from app.shared.models.auth_user import UserModel
from fastapi import Depends


class AuthRepository:
    def __init__(
        self,
        database: AsyncIOMotorDatabase,
    ):
        self.collection = database[Collections.USERS]

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
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> AuthRepository:
    return AuthRepository(database)
