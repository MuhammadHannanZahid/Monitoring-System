import asyncio

from app.service.mongo_db.mongo_controller import db_manager
from app.core.logger import get_logger

from app.seeder.seed_admin import AdminSeeder

logger = get_logger(__name__)


async def seed() -> None:
    logger.info("Starting database seeding...")

    await db_manager.connect()

    try:
        await AdminSeeder().run()
    finally:
        await db_manager.disconnect()

    logger.info("Database seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed())