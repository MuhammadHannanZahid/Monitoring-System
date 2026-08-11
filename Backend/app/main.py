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
from app.api.auth_profiles import router as auth_profiles_router
from app.core.config import settings
from app.core.database import db_manager
from app.core.exception_handlers import register_exception_handlers
from app.core.logger import get_logger
from app.modules.monitor.scheduler import MonitorScheduler
from app.modules.monitor.service import MonitorService
from app.modules.HTTP_monitor.service import HTTP_monitorRepository
from app.modules.API_monitor.service import API_monitorRepository
from app.modules.incident.service import IncidentRepository, IncidentService
from app.modules.monitor_results.service import (
    MonitorResultRepository,
    MonitorResultService,
)
from app.modules.monitor_state.service import MonitorStateRepository, MonitorStateService
from app.modules.monitor.checkers.checker_factory import CheckerFactory
from app.modules.monitor.repository_factory import MonitorRepositoryFactory
from app.modules.ping_monitor.service import PingMonitorRepository
from app.modules.heartbeat_monitor.service import HeartbeatMonitorRepository
from app.modules.auth_profiles.service import AuthProfileRepository
from app.modules.auth_profiles.token_manager import AccessTokenCookieManager
import app.modules.auth_profiles.token_manager as auth_token_state
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
api_router.include_router(auth_profiles_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")

    await db_manager.connect()

    engine = db_manager.engine

    http_repository = HTTP_monitorRepository(engine)
    api_repository = API_monitorRepository(engine)
    ping_repository = PingMonitorRepository(engine)
    heartbeat_repository = HeartbeatMonitorRepository(engine)
    auth_profile_repository = AuthProfileRepository(engine)
    await auth_profile_repository.create_indexes()
    incident_repository = IncidentRepository(engine)
    incident_service = IncidentService(incident_repository)
    monitor_result_repository = MonitorResultRepository(engine)
    monitor_result_service = MonitorResultService(monitor_result_repository)
    monitor_state_repository = MonitorStateRepository(engine)
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
