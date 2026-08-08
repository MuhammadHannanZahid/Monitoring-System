from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.HTTP_monitor.router import router as HTTP_monitor_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.API_monitor.router import router as api_monitor_router
from app.modules.ping_monitor.router import router as ping_router
from app.modules.heartbeat_monitor.router import router as heartbeat_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(HTTP_monitor_router)
api_router.include_router(dashboard_router)
api_router.include_router(api_monitor_router)
api_router.include_router(ping_router)
api_router.include_router(heartbeat_router)