from collections.abc import Callable
from fastapi import Depends
from app.modules.auth.dependencies import get_current_user
from app.shared.models.auth_user import UserModel
from app.shared.enums import UserRole
from app.shared.exceptions import AuthorizationError

def require_roles(*allowed_roles: UserRole) -> Callable:

    async def dependency(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role not in allowed_roles:
            raise AuthorizationError()

        return current_user
    return dependency

def require_admin() -> Callable:
    return require_roles(UserRole.ADMIN)


def require_viewer() -> Callable:
    return require_roles(
        UserRole.ADMIN,
        UserRole.VIEWER,
    )