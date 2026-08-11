import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.core.database import db_manager
from app.core.logger import get_logger
from app.core.security import password_service
from app.modules.users.service import UserRepository

from app.shared.models.auth_user import UserModel
from app.shared.models.auth_user import UserRole

from .base import BaseSeeder

logger = get_logger(__name__)


class AdminSeeder(BaseSeeder):
    async def run(self) -> None:
        load_dotenv()
        default_admin_username = os.environ["DEFAULT_ADMIN_USERNAME"]
        default_admin_password = os.environ["DEFAULT_ADMIN_PASSWORD"]
        repository = UserRepository(db_manager.get_engine())

        existing_admin = await repository.get_by_username(
            default_admin_username
        )

        if existing_admin:
            await repository.update_seed_admin()
            logger.info("Default admin already exists. Role and status verified.")
            return

        now = datetime.now(timezone.utc)

        admin = UserModel(
            username=default_admin_username,
            password_hash=password_service.hash_password(
                default_admin_password
            ),
            role=UserRole.ADMIN,
            refresh_token_hash=None,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_login=None,
        )

        await repository.create_user(admin)

        logger.info("Default admin created successfully.")
