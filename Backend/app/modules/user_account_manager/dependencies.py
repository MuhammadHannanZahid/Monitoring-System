from fastapi import Depends
from odmantic import AIOEngine
from app.service.mongo_db.mongo_controller import get_engine
from app.core.security import password_service
from app.modules.user_account_manager.service import UserService

def get_user_service(engine: AIOEngine = Depends(get_engine)) -> UserService:
    return UserService(engine, password_service)
