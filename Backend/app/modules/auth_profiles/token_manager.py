import asyncio
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

import httpx

from app.core.logger import get_logger
from app.modules.auth_profiles.repository import AuthProfileRepository
from app.shared.models.auth_profile import AuthProfileModel

logger = get_logger(__name__)


class AuthTokenError(RuntimeError):
    pass


@dataclass(frozen=True)
class CachedBearerToken:
    value: str
    refresh_at: float


class BearerTokenManager:
    def __init__(
        self,
        repository: AuthProfileRepository,
        client: httpx.AsyncClient | None = None,
        refresh_after: timedelta = timedelta(minutes=14),
        clock: Callable[[], float] = time.monotonic,
    ):
        self.repository = repository
        self.client = client or httpx.AsyncClient(follow_redirects=True)
        self.refresh_after_seconds = refresh_after.total_seconds()
        self.clock = clock
        self._owns_client = client is None
        self._cache: dict[str, CachedBearerToken] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_token(
        self,
        profile_id: str,
        *,
        force_refresh: bool = False,
    ) -> str:
        cached = self._cache.get(profile_id)
        if not force_refresh and self._is_valid(cached):
            return cached.value

        lock = self._locks.setdefault(profile_id, asyncio.Lock())
        async with lock:
            cached = self._cache.get(profile_id)
            if not force_refresh and self._is_valid(cached):
                return cached.value

            profile = await self.repository.get_by_id(profile_id)
            if profile is None:
                raise AuthTokenError(f"Auth profile '{profile_id}' was not found.")

            token, refresh_seconds = await self._fetch_token(profile)
            self._cache[profile_id] = CachedBearerToken(
                value=token,
                refresh_at=self.clock() + refresh_seconds,
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

    def _is_valid(self, cached: CachedBearerToken | None) -> bool:
        return cached is not None and self.clock() < cached.refresh_at

    async def _fetch_token(
        self,
        profile: AuthProfileModel,
    ) -> tuple[str, float]:
        request_data = {
            "method": profile.method,
            "url": profile.login_url,
            "headers": profile.headers,
        }
        if profile.credential_location == "form":
            request_data["data"] = profile.credentials
        else:
            request_data["json"] = profile.credentials

        try:
            response = await self.client.request(**request_data)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthTokenError(
                f"Authentication failed for profile '{profile.name}': {exc}"
            ) from exc

        token = self._get_nested_value(payload, profile.token_field)
        if not isinstance(token, str) or not token:
            raise AuthTokenError(
                f"Token field '{profile.token_field}' was missing from the "
                f"authentication response for profile '{profile.name}'."
            )

        refresh_seconds = self.refresh_after_seconds
        if profile.expires_in_field:
            expires_in = self._get_nested_value(payload, profile.expires_in_field)
            if isinstance(expires_in, str):
                try:
                    expires_in = float(expires_in)
                except ValueError:
                    expires_in = None
            if isinstance(expires_in, (int, float)) and expires_in > 0:
                safety_window = min(30.0, float(expires_in) * 0.1)
                refresh_seconds = min(
                    refresh_seconds,
                    max(0.0, float(expires_in) - safety_window),
                )

        logger.info("Bearer token refreshed for auth profile '%s'.", profile.name)
        return token, refresh_seconds

    @staticmethod
    def _get_nested_value(payload: object, field_path: str) -> object | None:
        value = payload
        for part in field_path.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value
