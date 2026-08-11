from fastapi import Depends
from app.modules.API_monitor.service import (
    API_monitorRepository,
    API_monitorService,
    get_API_monitor_repository,
)
from app.modules.auth_profiles.dependencies import get_auth_profile_repository
from app.modules.auth_profiles.service import AuthProfileRepository


def get_API_monitor_service(
    repository: API_monitorRepository = Depends(get_API_monitor_repository),
    auth_profile_repository: AuthProfileRepository = Depends(
        get_auth_profile_repository
    ),
) -> API_monitorService:
    return API_monitorService(repository, auth_profile_repository)
