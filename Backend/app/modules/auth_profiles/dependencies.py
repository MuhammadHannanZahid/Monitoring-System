from fastapi import Depends

from app.core.database import get_database
from app.modules.auth_profiles.repository import AuthProfileRepository
from app.modules.auth_profiles.service import AuthProfileService


def get_auth_profile_repository(database=Depends(get_database)) -> AuthProfileRepository:
    return AuthProfileRepository(database)


def get_auth_profile_service(
    repository: AuthProfileRepository = Depends(get_auth_profile_repository),
) -> AuthProfileService:
    return AuthProfileService(repository)
