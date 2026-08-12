from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.modules.auth_profiles.service import AuthProfileService


def get_auth_profile_service(
    engine: AIOEngine = Depends(get_engine),
) -> AuthProfileService:
    return AuthProfileService(engine)
