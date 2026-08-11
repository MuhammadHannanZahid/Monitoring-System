from contextlib import asynccontextmanager
import asyncio
from fastapi import APIRouter, FastAPI
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.HTTP_monitor import router as HTTP_monitor_router
from app.api.dashboard import router as dashboard_router
from app.api.API_monitor import router as api_monitor_router
from app.api.ping_monitor import router as ping_router
from app.api.heartbeat_monitor import router as heartbeat_router
from app.core.config import settings
from app.core.database import db_manager
from app.core.exception_handlers import register_exception_handlers
from app.core.logger import get_logger
from app.modules.monitor.scheduler import MonitorScheduler
from app.modules.monitor.service import MonitorService
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.modules.API_monitor.repository import API_monitorRepository
from app.modules.incident.repository import IncidentRepository
from app.modules.incident.service import IncidentService
from app.modules.monitor_results.repository import MonitorResultRepository
from app.modules.monitor_results.service import MonitorResultService
from app.modules.monitor_state.service import MonitorStateService
from app.modules.monitor_state.repository import MonitorStateRepository
from app.modules.monitor.checkers.checker_factory import CheckerFactory
from app.modules.monitor.repository_factory import MonitorRepositoryFactory
from app.modules.ping_monitor.repository import PingMonitorRepository
from app.modules.heartbeat_monitor.repository import HeartbeatMonitorRepository
from app.modules.auth_profiles.repository import AuthProfileRepository
from app.modules.auth_profiles.token_manager import AccessTokenCookieManager
import app.core.auth_tokens as auth_token_state
import app.core.scheduler as scheduler_state

logger = get_logger(__name__)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(HTTP_monitor_router)
api_router.include_router(dashboard_router)
api_router.include_router(api_monitor_router)
api_router.include_router(ping_router)
api_router.include_router(heartbeat_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")

    await db_manager.connect()

    database = db_manager.database

    http_repository = HTTP_monitorRepository(database)
    api_repository = API_monitorRepository(database)
    ping_repository = PingMonitorRepository(database)
    heartbeat_repository = HeartbeatMonitorRepository(database)
    auth_profile_repository = AuthProfileRepository(database)
    await auth_profile_repository.create_indexes()
    incident_repository = IncidentRepository(database)
    incident_service = IncidentService(incident_repository)
    monitor_result_repository = MonitorResultRepository(database)
    monitor_result_service = MonitorResultService(monitor_result_repository)
    monitor_state_repository = MonitorStateRepository(database)
    monitor_state_service = MonitorStateService(monitor_state_repository)

    auth_token_state.token_manager = AccessTokenCookieManager(auth_profile_repository)
    checker_factory = CheckerFactory(token_manager=auth_token_state.token_manager)

    repository_factory = MonitorRepositoryFactory(
        http_repository,
        api_repository,
        ping_repository,
        heartbeat_repository,
    )

    monitor_service = MonitorService(
        repository_factory=repository_factory,
        incident_service=incident_service,
        monitor_result_service=monitor_result_service,
        monitor_state_service=monitor_state_service,
        checker_factory=checker_factory,
    )

    scheduler_state.scheduler = MonitorScheduler(monitor_service=monitor_service)
    scheduler_task = asyncio.create_task(scheduler_state.scheduler.start())
    logger.info("Main scheduler: %s", scheduler_state)

    try:
        yield
    finally:
        await scheduler_state.scheduler.stop()
        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        await checker_factory.close()
        auth_token_state.token_manager = None
        await db_manager.disconnect()
        logger.info("Application stopped.")

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

register_exception_handlers(app)
app.include_router(api_router)
