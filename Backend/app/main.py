from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from app.api.api import api_router
from app.core.config import settings
from app.core.database import db_manager
from app.core.exception_handlers import register_exception_handlers
from app.core.logger import get_logger
from app.modules.monitor.scheduler import MonitorScheduler
from app.modules.monitor.service import MonitorService
from app.modules.website.repository import WebsiteRepository
from app.modules.website.service import WebsiteService
from app.modules.incident.repository import IncidentRepository
from app.modules.incident.service import IncidentService
from app.modules.monitor_results.repository import MonitorResultRepository
from app.modules.monitor_results.service import MonitorResultService

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")

    await db_manager.connect()

    database = db_manager.database

    website_repository = WebsiteRepository(database)
    incident_repository = IncidentRepository(database)
    monitor_result_repository = MonitorResultRepository(database)

    website_service = WebsiteService(website_repository)
    incident_service = IncidentService(incident_repository)
    monitor_result_service = MonitorResultService(monitor_result_repository)

    monitor_service = MonitorService(website_repository=website_repository, incident_service=incident_service, monitor_result_service=monitor_result_service)

    scheduler = MonitorScheduler(monitor_service=monitor_service, website_service=website_service)
    scheduler_task = asyncio.create_task(scheduler.start())

    try:
        yield
    finally:
        await scheduler.stop()
        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        await db_manager.disconnect()
        logger.info("Application stopped.")

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

register_exception_handlers(app)
app.include_router(api_router)