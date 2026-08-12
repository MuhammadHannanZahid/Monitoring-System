from fastapi import Depends
from odmantic import AIOEngine
from app.core.database import get_engine
from app.modules.API_monitor.service import API_monitorService
from app.modules.auth_profiles.dependencies import get_auth_profile_service
from app.modules.auth_profiles.service import AuthProfileService

def get_API_monitor_service(engine: AIOEngine = Depends(get_engine), auth_profile_service: AuthProfileService = Depends(get_auth_profile_service)) -> API_monitorService:
    return API_monitorService(engine, auth_profile_service)
