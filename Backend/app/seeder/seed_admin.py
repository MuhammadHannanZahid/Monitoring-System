from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import db_manager
from app.core.logger import get_logger
from app.core.security import password_service

from app.modules.auth.models import UserModel
from app.shared.database_constants import Collections
from app.shared.enums import UserRole

from .base import BaseSeeder

logger = get_logger(__name__)


class AdminSeeder(BaseSeeder):
    async def run(self) -> None:
        database = db_manager.get_database()
        users = database[Collections.USERS]

        existing_admin = await users.find_one(
            {"username": settings.default_admin_username}
        )

        if existing_admin:
            logger.info("Default admin already exists. Skipping seeder.")
            return

        now = datetime.now(timezone.utc)

        admin = UserModel(
            username=settings.default_admin_username,
            password_hash=password_service.hash_password(
                settings.default_admin_password
            ),
            role=UserRole.ADMIN,
            refresh_token_hash=None,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_login=None,
        )

        document = admin.model_dump()
        document.pop("id", None)

        await users.insert_one(document)

        logger.info("Default admin created successfully.")