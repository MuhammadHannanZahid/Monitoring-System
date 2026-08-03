from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError
from bson.codec_options import CodecOptions
from datetime import timezone
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self):
        self._client: AsyncIOMotorClient | None = None
        self._database: AsyncIOMotorDatabase | None = None

    @property
    def client(self) -> AsyncIOMotorClient:
        if self._client is None:
            raise RuntimeError("MongoDB client has not been initialized.")
        return self._client

    @property
    def database(self) -> AsyncIOMotorDatabase:
        if self._database is None:
            raise RuntimeError("MongoDB has not been initialized.")
        return self._database

    async def connect(self) -> None:
        try:
            logger.info("Connecting to MongoDB...")
            self._client = AsyncIOMotorClient(settings.mongo_uri)
            self._database = self._client.get_database(
                settings.database_name,
                codec_options=CodecOptions(tz_aware=True, tzinfo=timezone.utc)
            )
            await self._client.admin.command("ping")
            logger.info("MongoDB connected successfully.")

        except PyMongoError:
            logger.exception("Failed to connect to MongoDB.")
            raise

    async def disconnect(self) -> None:
        if self._client:
            logger.info("Closing MongoDB connection.")
            self._client.close()
            logger.info("MongoDB connection closed.")

            self._client = None
            self._database = None


    def get_database(self) -> AsyncIOMotorDatabase:
        return self.database

db_manager = DatabaseManager()

async def get_database() -> AsyncIOMotorDatabase:
    return db_manager.get_database()