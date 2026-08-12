import os

from dotenv import load_dotenv

from app.core.database import db_manager
from app.core.logger import get_logger
from app.core.security import password_service
from app.modules.users.service import UserService

from .base import BaseSeeder

logger = get_logger(__name__)


class AdminSeeder(BaseSeeder):
    async def run(self) -> None:
        load_dotenv()
        default_admin_username = os.environ["DEFAULT_ADMIN_USERNAME"]
        default_admin_password = os.environ["DEFAULT_ADMIN_PASSWORD"]
        service = UserService(db_manager.get_engine(), password_service)
        created = await service.ensure_default_admin(
            default_admin_username,
            default_admin_password,
        )
        if not created:
            logger.info("Default admin already exists. Role and status verified.")
            return
        logger.info("Default admin created successfully.")
