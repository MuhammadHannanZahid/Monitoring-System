import os
from collections.abc import Callable

from dotenv import load_dotenv
from fastapi import Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from odmantic import AIOEngine

from app.core.jwt import jwt_service
from app.core.security import password_service, refresh_token_service
from app.modules.auth_manager.service import AuthService
from app.service.constants import Messages
from app.service.exceptions import AuthenticationError, AuthorizationError
from app.service.mongo_db.mongo_controller import get_engine
from app.service.mongo_db.shared_models.db_user_account_model import (
    AuthTokens,
    UserModel,
    UserRole,
)

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"
AUTH_COOKIE_PATH = "/api"

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(
    engine: AIOEngine = Depends(get_engine),
) -> AuthService:
    return AuthService(
        engine=engine,
        password_service=password_service,
        jwt_service=jwt_service,
        refresh_token_service=refresh_token_service,
    )


def _cookie_secure() -> bool:
    load_dotenv()
    return os.getenv("APP_ENV", "production").lower() not in {
        "development",
        "local",
        "test",
    }


def set_auth_cookies(response: Response, tokens: AuthTokens) -> None:
    load_dotenv()
    secure = _cookie_secure()
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=tokens.access_token,
        max_age=int(os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"]) * 60,
        path=AUTH_COOKIE_PATH,
        secure=secure,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=tokens.refresh_token,
        max_age=int(os.environ["REFRESH_TOKEN_EXPIRE_DAYS"]) * 24 * 60 * 60,
        path=AUTH_COOKIE_PATH,
        secure=secure,
        httponly=True,
        samesite="lax",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        ACCESS_TOKEN_COOKIE,
        path=AUTH_COOKIE_PATH,
        secure=_cookie_secure(),
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        REFRESH_TOKEN_COOKIE,
        path=AUTH_COOKIE_PATH,
        secure=_cookie_secure(),
        httponly=True,
        samesite="lax",
    )


async def get_current_user(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
) -> UserModel:
    candidate_tokens = []
    if credentials is not None:
        candidate_tokens.append(credentials.credentials)
    cookie_access_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if cookie_access_token is not None:
        candidate_tokens.append(cookie_access_token)

    payload = None
    for token in candidate_tokens:
        try:
            payload = service.jwt_service.verify_access_token(token)
            break
        except JWTError:
            continue

    if payload is None:
        refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
        if refresh_token is None:
            raise AuthenticationError(Messages.INVALID_CREDENTIALS)
        tokens = await service.refresh_tokens(refresh_token)
        set_auth_cookies(response, tokens)
        response.headers["X-Access-Token-Refreshed"] = "true"
        payload = service.jwt_service.verify_access_token(tokens.access_token)

    user = await service.get_current_user(payload["sub"])
    if not user.is_active:
        raise AuthenticationError("User account is disabled.")
    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    async def dependency(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        if current_user.role not in allowed_roles:
            raise AuthorizationError()
        return current_user

    return dependency


def require_admin() -> Callable:
    return require_roles(UserRole.ADMIN)


def require_viewer() -> Callable:
    return require_roles(UserRole.ADMIN, UserRole.VIEWER)
