from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.core.security import password_service
from app.modules.users.service import UserService


def get_user_service(
    engine: AIOEngine = Depends(get_engine),
) -> UserService:
    return UserService(engine, password_service)
