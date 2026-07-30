from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import get_logger
from app.core.database import db_manager, get_database
from app.core.exception_handlers import (register_exception_handlers)
from app.api.api import api_router
import asyncio
from app.modules.monitor.scheduler import MonitorScheduler
from app.modules.monitor.service import MonitorService, WebsiteService
from app.modules.website.repository import WebsiteRepository

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")

    await db_manager.connect()
    yield
    await db_manager.disconnect()

    logger.info("Application stopped.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    database = get_database()
    website_repository = WebsiteRepository(database)
    website_service = WebsiteService(website_repository)
    monitor_service = MonitorService(website_repository)
    scheduler = MonitorScheduler(monitor_service=monitor_service, website_service=website_service)
    scheduler_task = asyncio.create_task(scheduler.start())

    yield
    await scheduler.stop()
    scheduler_task.cancel()

    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(api_router)