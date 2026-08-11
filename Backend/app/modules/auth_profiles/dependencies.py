from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.modules.auth_profiles.service import AuthProfileRepository, AuthProfileService

def get_auth_profile_repository(
    engine: AIOEngine = Depends(get_engine),
) -> AuthProfileRepository:
    return AuthProfileRepository(engine)

def get_auth_profile_service(repository: AuthProfileRepository = Depends(get_auth_profile_repository)) -> AuthProfileService:
    return AuthProfileService(repository)
