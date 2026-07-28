from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.shared.database_constants import Collections
from app.shared.models.auth_user import UserModel
from app.shared.enums import UserRole
from app.core.config import settings

class UserRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database[Collections.USERS]

    async def update_seed_admin(self) -> None:
        await self.collection.update_one(
            {"username": settings.admin_username},
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

def get_user_repository(database: AsyncIOMotorDatabase = Depends(get_database)) -> UserRepository:
    return UserRepository(database)