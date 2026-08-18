from contextlib import asynccontextmanager
import asyncio
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from app.routes.auth_routes import router as auth_router
from app.routes.user_account_routes import router as users_router
from app.routes.http_monitor_routes import router as HTTP_monitor_router
from app.routes.insight_routes import router as dashboard_router
from app.routes.api_monitor_routes import router as api_monitor_router
from app.routes.ping_monitor_routes import router as ping_router
from app.routes.heartbeat_monitor_routes import router as heartbeat_router
from app.routes.orion_login_routes import router as auth_profiles_router
from app.routes.realtime_routes import router as realtime_router
from app.service.mongo_db.mongo_controller import db_manager
from app.core.exception_handlers import register_exception_handlers
from app.core.logger import get_logger
from app.modules.monitoring_controller.scheduler import MonitorScheduler
from app.modules.monitoring_controller.monitoring_controller import MonitorManager
from app.modules.http_monitor_manager.http_monitor_manager import HTTP_monitorManager
from app.modules.api_monitor_manager.api_monitor_manager import API_monitorManager
from app.modules.incident_manager.incident_manager import IncidentManager
from app.modules.monitoring_controller.monitor_results_manager.monitor_results_manager import MonitorResultManager
from app.modules.monitoring_controller.monitor_state_manager.monitor_state_manager import MonitorStateManager
from app.modules.monitoring_controller.checkers.checker_factory import CheckerFactory
from app.modules.ping_monitor_manager.ping_monitor_manager import PingMonitorManager
from app.modules.heartbeat_monitor_manager.heartbeat_monitor_manager import HeartbeatMonitorManager
from app.modules.orion_login_manager.orion_login_manager import AuthProfileManager
from app.modules.orion_login_manager.orion_token_manager import AccessTokenCookieManager
from app.modules.insight_manager.insight_manager import DashboardManager
from app.modules.auth_manager.auth_manager import password_service
from app.modules.user_account_manager.user_account_manager import UserManager
from app.service.realtime import realtime_broker
from app.service.exceptions import NotFoundError
import app.modules.orion_login_manager.orion_token_manager as auth_token_state
import app.modules.monitoring_controller.scheduler as scheduler_state

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
api_router.include_router(realtime_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")

    await db_manager.connect()

    engine = db_manager.engine

    auth_profile_service = AuthProfileManager(engine)
    await auth_profile_service.create_indexes()
    http_monitor_service = HTTP_monitorManager(engine)
    api_monitor_manager = API_monitorManager(engine, auth_profile_service)
    ping_monitor_service = PingMonitorManager(engine)
    heartbeat_monitor_service = HeartbeatMonitorManager(engine)
    incident_service = IncidentManager(engine)
    monitor_result_service = MonitorResultManager(engine)
    monitor_state_service = MonitorStateManager(engine)
    user_service = UserManager(engine, password_service)

    auth_token_state.token_manager = AccessTokenCookieManager(auth_profile_service)
    checker_factory = CheckerFactory(token_manager=auth_token_state.token_manager)

    monitor_service = MonitorManager(
        http_monitor_service=http_monitor_service,
        api_monitor_manager=api_monitor_manager,
        ping_monitor_service=ping_monitor_service,
        heartbeat_monitor_service=heartbeat_monitor_service,
        incident_service=incident_service,
        monitor_result_service=monitor_result_service,
        monitor_state_service=monitor_state_service,
        checker_factory=checker_factory,
    )
    heartbeat_monitor_service.monitor_service = monitor_service

    dashboard_service = DashboardManager(
        monitor_service=monitor_service,
        monitor_result_service=monitor_result_service,
        incident_service=incident_service,
    )

    async def build_realtime_snapshot(changed, include_admin):
        (
            summary,
            incidents,
            activity,
            overviews,
        ) = await asyncio.gather(
            dashboard_service.get_summary(),
            dashboard_service.get_recent_incidents(),
            dashboard_service.get_recent_activity(),
            dashboard_service.get_monitor_overviews(),
        )
        changed_monitor_details = {}
        for kind, entity_id in changed:
            if kind != "monitor" or entity_id is None:
                continue
            try:
                changed_monitor_details[entity_id] = (
                    await dashboard_service.get_monitor_detail(entity_id)
                )
            except NotFoundError:
                pass
        common = {
            "generated_at": datetime.now(timezone.utc),
            "summary": summary,
            "incidents": incidents,
            "activity": activity,
            "overviews": overviews,
            "changed_monitor_details": changed_monitor_details,
        }
        admin = common
        if include_admin:
            (
                http_monitors,
                api_monitors,
                ping_monitors,
                heartbeat_monitors,
                auth_profiles,
                users,
            ) = await asyncio.gather(
                http_monitor_service.list_monitors(),
                api_monitor_manager.list_monitors(),
                ping_monitor_service.list_monitors(),
                heartbeat_monitor_service.list_monitors(),
                auth_profile_service.list_profiles(),
                user_service.list_users(),
            )
            admin = {
                **common,
                "resources": {
                    "HTTP": http_monitors,
                    "API": api_monitors,
                    "ping": ping_monitors,
                    "heartbeat": heartbeat_monitors,
                    "auth_profiles": auth_profiles,
                    "users": users,
                },
            }
        return common, admin

    realtime_broker.configure(build_realtime_snapshot)

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
        await realtime_broker.shutdown()
        auth_token_state.token_manager = None
        await db_manager.disconnect()
        logger.info("Application stopped.")

load_dotenv()
app = FastAPI(
    title=os.environ["APP_NAME"],
    version=os.environ["APP_VERSION"],
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(api_router)
