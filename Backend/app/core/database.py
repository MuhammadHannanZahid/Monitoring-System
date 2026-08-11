from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError
from bson.codec_options import CodecOptions
from datetime import timezone
from app.core.config import settings
from app.core.logger import get_logger
from pymongo import ASCENDING, DESCENDING
from app.shared.database_constants import Collections

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
            await self._create_indexes()
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

    async def _create_indexes(self) -> None:
        await self._create_monitor_result_indexes()
        await self._create_incident_indexes()
        await self._create_heartbeat_indexes()
        logger.info("MongoDB indexes initialized.")

    async def _create_monitor_result_indexes(self) -> None:
        collection = self.database[Collections.MONITOR_RESULTS]
        await collection.create_index([("monitor_id", ASCENDING)])
        await collection.create_index([("checked_at", DESCENDING)])
        await collection.create_index([("monitor_id", ASCENDING), ("checked_at", DESCENDING)])
        await collection.create_index([("monitor_id", ASCENDING), ("is_slow", ASCENDING)])
        await collection.create_index([("monitor_id", ASCENDING), ("success", ASCENDING)])
        logger.info("Monitor Result indexes initialized.")

    async def _create_incident_indexes(self) -> None:
        collection = self.database[Collections.INCIDENTS]
        await collection.create_index([("monitor_id", ASCENDING), ("resolved_at", ASCENDING)])
        await collection.create_index([("monitor_id", ASCENDING), ("monitor_type", ASCENDING), ("resolved_at", ASCENDING)])
        await collection.create_index([("started_at", DESCENDING)])
        await collection.create_index([("is_resolved", ASCENDING)])
        logger.info("Incident indexes initialized.")

    async def _create_heartbeat_indexes(self) -> None:
        collection = self.database[Collections.HEARTBEAT_MONITORS]
        await collection.create_index("heartbeat_token_hash", unique=True)
        await collection.create_index("is_active")
        await collection.create_index("name")
        logger.info("Heartbeat indexes initialized.")

    def get_database(self) -> AsyncIOMotorDatabase:
        return self.database

db_manager = DatabaseManager()

async def get_database() -> AsyncIOMotorDatabase:
    return db_manager.get_database()