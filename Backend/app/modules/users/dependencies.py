from fastapi import Depends
from app.core.security import password_service
from app.modules.users.repository import UserRepository, get_user_repository
from app.modules.users.service import UserService

def get_user_service(repository: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(
        repository=repository,
        password_service=password_service,
    )