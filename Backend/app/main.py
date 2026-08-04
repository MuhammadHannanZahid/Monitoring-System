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
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.modules.HTTP_monitor.service import HTTP_monitorService
from app.modules.API_monitor.service import API_monitorService
from app.modules.API_monitor.repository import API_monitorRepository
from app.modules.incident.repository import IncidentRepository
from app.modules.incident.service import IncidentService
from app.modules.monitor_results.repository import MonitorResultRepository
from app.modules.monitor_results.service import MonitorResultService
from app.modules.monitor_state.service import MonitorStateService
from app.modules.monitor_state.repository import MonitorStateRepository
from app.modules.monitor.checkers.checker_factory import CheckerFactory

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")

    await db_manager.connect()

    database = db_manager.database

    HTTP_monitor_repository = HTTP_monitorRepository(database)
    API_monitor_repository = API_monitorRepository(database)
    incident_repository = IncidentRepository(database)
    monitor_result_repository = MonitorResultRepository(database)

    HTTP_monitor_service = HTTP_monitorService(HTTP_monitor_repository)
    API_monitor_service = API_monitorService(API_monitor_repository)
    incident_service = IncidentService(incident_repository)
    monitor_result_service = MonitorResultService(monitor_result_repository)

    monitor_state_repository = MonitorStateRepository(database)
    monitor_state_service = MonitorStateService(monitor_state_repository)

    checker_factory = CheckerFactory()

    repository_factory = MonitorRepositoryFactory(
        http_repository,
        api_repository,
    )

    monitor_service = MonitorService(
        repository_factory=repository_factory,
        incident_service=incident_service,
        monitor_result_service=monitor_result_service,
        monitor_state_service=monitor_state_service,
        checker_factory=checker_factory,
    )

    scheduler = MonitorScheduler(
        http_monitor_service=HTTP_monitor_service,
        api_monitor_service=API_monitor_service,
        monitor_service=monitor_service,
    )
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

        await checker_factory.close()
        await db_manager.disconnect()
        logger.info("Application stopped.")

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

register_exception_handlers(app)
app.include_router(api_router)