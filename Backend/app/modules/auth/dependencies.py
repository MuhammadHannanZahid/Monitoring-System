from fastapi import Depends
from app.core.jwt import jwt_service
from app.core.security import (password_service, refresh_token_service,)
from app.modules.auth.repository import (AuthRepository, get_auth_repository,)
from app.modules.auth.service import AuthService
from jose import JWTError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.shared.models.user import UserModel
from app.shared.exceptions import AuthenticationError
from app.shared.constants import Messages

def get_auth_service(repository: AuthRepository = Depends(get_auth_repository)) -> AuthService:

    return AuthService(
        repository=repository,
        password_service=password_service,
        jwt_service=jwt_service,
        refresh_token_service=refresh_token_service,
    )

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service)) -> UserModel:

    token = credentials.credentials
    try:
        payload = service.jwt_service.verify_access_token(token)
    except JWTError:
        raise AuthenticationError(Messages.INVALID_CREDENTIALS)

    user = await service.get_current_user(payload["sub"])
    if not user.is_active:
        raise AuthenticationError("User account is disabled.")
    return user