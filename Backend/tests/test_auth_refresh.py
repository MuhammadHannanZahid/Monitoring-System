import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import Request, Response

from app.core.jwt import JWTService
from app.core.security import PasswordService, RefreshTokenService
from app.main import app
from app.modules.auth_manager.dependencies import (
    REFRESH_TOKEN_COOKIE,
    get_current_user,
    set_auth_cookies,
)
from app.modules.auth_manager.service import AuthService
from app.service.exceptions import AuthenticationError
from app.service.mongo_db.shared_models.db_orion_login_model import AuthTokens, TokenType, UserModel, UserRole


USER_ID = "507f1f77bcf86cd799439011"


class FakeAuthCollection:
    def __init__(self, user: UserModel):
        self.user = user

    async def find_one(self, query: dict) -> dict | None:
        if "username" in query and query["username"] != self.user.username:
            return None
        if "_id" in query and str(query["_id"]) != self.user.id:
            return None
        if (
            "refresh_token_hash" in query
            and query["refresh_token_hash"] != self.user.refresh_token_hash
        ):
            return None
        document = self.user.model_dump()
        document.pop("id", None)
        document["_id"] = ObjectId(self.user.id)
        return document

    async def update_one(self, query: dict, update: dict):
        if (
            await self.find_one(query) is None
        ):
            return SimpleNamespace(matched_count=0, modified_count=0)
        for field, value in update["$set"].items():
            setattr(self.user, field, value)
        return SimpleNamespace(matched_count=1, modified_count=1)


class FakeAuthEngine:
    def __init__(self, collection: FakeAuthCollection):
        self.database = {"users": collection}


def make_user() -> UserModel:
    now = datetime.now(timezone.utc)
    return UserModel(
        id=USER_ID,
        username="viewer",
        password_hash="unused",
        role=UserRole.VIEWER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def make_auth_service(collection: FakeAuthCollection) -> AuthService:
    return AuthService(
        engine=FakeAuthEngine(collection),
        password_service=PasswordService(),
        jwt_service=JWTService(),
        refresh_token_service=RefreshTokenService(),
    )


def test_refresh_token_uses_configured_lifetime(monkeypatch):
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    jwt_service = JWTService()

    token, expires_at = jwt_service.create_refresh_token(
        user_id=USER_ID,
        username="viewer",
        role=UserRole.VIEWER,
    )
    payload = jwt_service.verify_refresh_token(token)

    assert payload["type"] == TokenType.REFRESH.value
    assert payload["sub"] == USER_ID
    assert payload["exp"] - payload["iat"] == 7 * 24 * 60 * 60
    assert int(expires_at.timestamp()) == payload["exp"]


def test_login_stores_an_expiring_refresh_token(monkeypatch):
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "14")
    user = make_user()
    collection = FakeAuthCollection(user)
    service = make_auth_service(collection)
    user.password_hash = service.password_service.hash_password("password123")

    tokens = asyncio.run(service.login(user.username, "password123"))
    payload = service.jwt_service.verify_refresh_token(tokens.refresh_token)

    assert collection.user.refresh_token_hash is not None
    assert collection.user.refresh_token_expires_at is not None
    assert payload["exp"] - payload["iat"] == 14 * 24 * 60 * 60


def test_refresh_rotates_token_and_rejects_replay(monkeypatch):
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")
    user = make_user()
    collection = FakeAuthCollection(user)
    service = make_auth_service(collection)

    refresh_token, expires_at = service.jwt_service.create_refresh_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    user.refresh_token_hash = service.refresh_token_service.hash_token(
        refresh_token
    )
    user.refresh_token_expires_at = expires_at

    refreshed = asyncio.run(service.refresh_tokens(refresh_token))

    assert refreshed.refresh_token != refresh_token
    assert service.jwt_service.verify_access_token(refreshed.access_token)[
        "sub"
    ] == USER_ID
    assert service.jwt_service.verify_refresh_token(refreshed.refresh_token)[
        "sub"
    ] == USER_ID

    with pytest.raises(AuthenticationError):
        asyncio.run(service.refresh_tokens(refresh_token))


def test_refresh_route_is_not_exposed():
    assert "/api/auth/refresh" not in app.openapi()["paths"]


def test_auth_cookies_are_http_only_and_scoped_to_api(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")
    response = Response()

    set_auth_cookies(
        response,
        AuthTokens(access_token="access", refresh_token="refresh"),
    )

    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 2
    assert all("HttpOnly" in cookie for cookie in cookies)
    assert all("Path=/api" in cookie for cookie in cookies)
    assert all("SameSite=lax" in cookie for cookie in cookies)


def test_protected_request_automatically_refreshes_from_cookie(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")
    user = make_user()
    collection = FakeAuthCollection(user)
    service = make_auth_service(collection)
    refresh_token, expires_at = service.jwt_service.create_refresh_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    user.refresh_token_hash = service.refresh_token_service.hash_token(
        refresh_token
    )
    user.refresh_token_expires_at = expires_at
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/auth/me",
            "query_string": b"",
            "headers": [
                (
                    b"cookie",
                    f"{REFRESH_TOKEN_COOKIE}={refresh_token}".encode(),
                )
            ],
        }
    )
    response = Response()

    current_user = asyncio.run(
        get_current_user(
            request=request,
            response=response,
            credentials=None,
            service=service,
        )
    )

    assert current_user.id == USER_ID
    assert response.headers["X-Access-Token-Refreshed"] == "true"
    assert len(response.headers.getlist("set-cookie")) == 2
