from fastapi import FastAPI

from app.core.config import settings
from app.core.logger import logger

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

logger.info("========================================")
logger.info("%s started", settings.app_name)
logger.info("Environment : %s", settings.app_env)
logger.info("Version     : %s", settings.app_version)
logger.info("========================================")