from fastapi import Depends
from odmantic import AIOEngine
from app.service.mongo_db.mongo_controller import get_engine
from app.modules.api_monitor_manager.service import API_monitorService
from app.modules.orion_login_manager.dependencies import get_auth_profile_service
from app.modules.orion_login_manager.service import AuthProfileService

def get_API_monitor_service(engine: AIOEngine = Depends(get_engine), auth_profile_service: AuthProfileService = Depends(get_auth_profile_service)) -> API_monitorService:
    return API_monitorService(engine, auth_profile_service)
