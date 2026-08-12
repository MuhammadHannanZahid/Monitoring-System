from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import TYPE_CHECKING, Callable
import httpx
from app.core.logger import get_logger
from app.service.mongo_db.shared_models.models.auth_profile import AuthProfileModel

if TYPE_CHECKING:
    from app.modules.orion_login_manager.service import AuthProfileService

logger = get_logger(__name__)

ACCESS_TOKEN_COOKIE_NAME = "access_token"
TOKEN_CACHE_TTL_SECONDS = 14 * 60

class AuthTokenError(RuntimeError):
    pass

@dataclass(frozen=True)
class CachedAccessToken:
    value: str
    expires_at: float

class AccessTokenCookieManager:
    def __init__(self, auth_profile_service: AuthProfileService, client: httpx.AsyncClient | None = None, clock: Callable[[], float] = time.monotonic):
        self.auth_profile_service = auth_profile_service
        self.client = client or httpx.AsyncClient(follow_redirects=True)
        self.clock = clock
        self._owns_client = client is None
        self._cache: dict[str, CachedAccessToken] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_token(self, profile_id: str, *, force_refresh: bool = False) -> str:
        cached = self._cache.get(profile_id)
        if not force_refresh and self._is_valid(cached):
            return cached.value

        lock = self._locks.setdefault(profile_id, asyncio.Lock())
        async with lock:
            cached = self._cache.get(profile_id)
            if not force_refresh and self._is_valid(cached):
                return cached.value

            profile = await self.auth_profile_service.get_profile(profile_id)
            if profile is None:
                raise AuthTokenError(f"Auth profile '{profile_id}' was not found.")

            token = await self._fetch_token(profile)
            self._cache[profile_id] = CachedAccessToken(
                value=token,
                expires_at=self.clock() + TOKEN_CACHE_TTL_SECONDS,
            )
            return token

    def invalidate(self, profile_id: str) -> None:
        self._cache.pop(profile_id, None)

    def clear(self) -> None:
        self._cache.clear()

    async def close(self) -> None:
        self.clear()
        if self._owns_client:
            await self.client.aclose()

    def _is_valid(self, cached: CachedAccessToken | None) -> bool:
        return cached is not None and self.clock() < cached.expires_at

    async def _fetch_token(self, profile: AuthProfileModel) -> str:
        try:
            response = await self.client.request(
                method=profile.method,
                url=profile.login_url,
                headers=profile.headers,
                data=profile.credentials,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AuthTokenError(f"Authentication failed for profile '{profile.name}': {exc}") from exc

        token = self._extract_access_token_cookie(response)
        if token is None:
            raise AuthTokenError(
                f"The '{ACCESS_TOKEN_COOKIE_NAME}' cookie was missing from the "
                f"login response for profile '{profile.name}'."
            )

        logger.info("Access-token cookie refreshed for auth profile '%s'.", profile.name)
        return token

    @staticmethod
    def _extract_access_token_cookie(response: httpx.Response) -> str | None:
        for candidate in reversed([*response.history, response]):
            for header in candidate.headers.get_list("set-cookie"):
                cookies = SimpleCookie()
                cookies.load(header)
                morsel = cookies.get(ACCESS_TOKEN_COOKIE_NAME)
                if morsel is not None and morsel.value:
                    return morsel.value
        return None

token_manager: AccessTokenCookieManager | None = None