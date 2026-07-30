from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.website.router import router as website_router
from app.modules.dashboard.router import router as dashboard_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(website_router)
api_router.include_router(dashboard_router)