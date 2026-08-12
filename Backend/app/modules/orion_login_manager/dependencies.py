from fastapi import Depends
from odmantic import AIOEngine
from app.service.mongo_db.mongo_controller import get_engine
from app.modules.orion_login_manager.service import AuthProfileService

def get_auth_profile_service(engine: AIOEngine = Depends(get_engine)) -> AuthProfileService:
    return AuthProfileService(engine)
