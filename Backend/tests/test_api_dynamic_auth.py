import asyncio
from datetime import datetime, timezone

import httpx

from app.modules.API_monitor.schemas import CreateApiMonitorRequest
from app.modules.API_monitor.service import API_monitorService
from app.modules.auth_profiles.schemas import CreateAuthProfileRequest
from app.modules.auth_profiles.service import AuthProfileService
from app.modules.auth_profiles.token_manager import BearerTokenManager
from app.modules.monitor.checkers.api_checker import ApiChecker
from app.shared.enums import MonitorStatus
from app.shared.models.api_monitor import APIMonitorModel
from app.shared.models.auth_profile import AuthProfileModel


def make_auth_profile(**changes) -> AuthProfileModel:
    now = datetime.now(timezone.utc)
    values = {
        "id": "507f1f77bcf86cd799439011",
        "name": "Service login",
        "login_url": "https://service.test/login",
        "method": "POST",
        "credentials": {"username": "monitor", "password": "secret"},
        "created_at": now,
        "updated_at": now,
    }
    values.update(changes)
    return AuthProfileModel(**values)


def make_api_monitor(**changes) -> APIMonitorModel:
    now = datetime.now(timezone.utc)
    values = {
        "id": "507f1f77bcf86cd799439012",
        "name": "Protected API",
        "url": "https://service.test/protected",
        "method": "GET",
        "headers": {"X-Monitor": "true"},
        "expected_status_code": 200,
        "check_interval": 60,
        "timeout": 10,
        "auth_profile_id": "507f1f77bcf86cd799439011",
        "created_at": now,
        "updated_at": now,
    }
    values.update(changes)
    return APIMonitorModel(**values)


class FakeAuthProfileRepository:
    def __init__(self, profile):
        self.profile = profile

    async def get_by_id(self, profile_id):
        if self.profile is None or self.profile.id != profile_id:
            return None
        return self.profile


def test_bearer_token_is_cached_for_fourteen_minutes():
    profile = make_auth_profile()
    repository = FakeAuthProfileRepository(profile)
    current_time = [0.0]
    login_requests = []

    def handle_login(request: httpx.Request) -> httpx.Response:
        login_requests.append(request)
        return httpx.Response(
            200,
            json={
                "access_token": f"token-{len(login_requests)}",
                "expires_in": 3600,
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle_login))
    manager = BearerTokenManager(
        repository,
        client=client,
        clock=lambda: current_time[0],
    )

    async def scenario():
        first = await manager.get_token(profile.id)
        current_time[0] = 839
        cached = await manager.get_token(profile.id)
        current_time[0] = 840
        refreshed = await manager.get_token(profile.id)
        await client.aclose()
        return first, cached, refreshed

    first, cached, refreshed = asyncio.run(scenario())

    assert (first, cached, refreshed) == ("token-1", "token-1", "token-2")
    assert len(login_requests) == 2
    assert login_requests[0].method == "POST"
    assert login_requests[0].read() == b'{"username":"monitor","password":"secret"}'


def test_token_refreshes_before_a_shorter_server_expiration():
    profile = make_auth_profile()
    repository = FakeAuthProfileRepository(profile)
    current_time = [0.0]
    login_count = 0

    def handle_login(request: httpx.Request) -> httpx.Response:
        nonlocal login_count
        login_count += 1
        return httpx.Response(
            200,
            json={"access_token": f"short-{login_count}", "expires_in": 100},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle_login))
    manager = BearerTokenManager(
        repository,
        client=client,
        clock=lambda: current_time[0],
    )

    async def scenario():
        first = await manager.get_token(profile.id)
        current_time[0] = 89
        cached = await manager.get_token(profile.id)
        current_time[0] = 90
        refreshed = await manager.get_token(profile.id)
        await client.aclose()
        return first, cached, refreshed

    first, cached, refreshed = asyncio.run(scenario())

    assert (first, cached, refreshed) == ("short-1", "short-1", "short-2")
    assert login_count == 2


class FakeTokenManager:
    def __init__(self):
        self.calls = []

    async def get_token(self, profile_id, *, force_refresh=False):
        self.calls.append((profile_id, force_refresh))
        return "fresh-token" if force_refresh else "cached-token"


def test_api_checker_injects_bearer_token_and_retries_one_unauthorized_request():
    token_manager = FakeTokenManager()
    authorization_headers = []

    def handle_api(request: httpx.Request) -> httpx.Response:
        authorization = request.headers.get("Authorization")
        authorization_headers.append(authorization)
        if authorization == "Bearer cached-token":
            return httpx.Response(401, json={"detail": "expired"})
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle_api))
    checker = ApiChecker(token_manager=token_manager, client=client)
    monitor = make_api_monitor()

    async def scenario():
        result = await checker.check(monitor)
        await client.aclose()
        return result

    result = asyncio.run(scenario())

    assert result.status == MonitorStatus.UP
    assert result.success is True
    assert authorization_headers == [
        "Bearer cached-token",
        "Bearer fresh-token",
    ]
    assert token_manager.calls == [
        (monitor.auth_profile_id, False),
        (monitor.auth_profile_id, True),
    ]
    assert monitor.headers == {"X-Monitor": "true"}


class FakeApiMonitorRepository:
    def __init__(self):
        self.monitor = None

    async def get_by_name(self, name):
        return None

    async def get_by_url(self, url):
        return None

    async def create(self, monitor):
        self.monitor = monitor
        return "507f1f77bcf86cd799439012"


def test_api_monitor_validates_and_persists_auth_profile_reference():
    profile = make_auth_profile()
    api_repository = FakeApiMonitorRepository()
    profile_repository = FakeAuthProfileRepository(profile)
    service = API_monitorService(api_repository, profile_repository)
    request = CreateApiMonitorRequest(
        name="Protected API",
        url="https://service.test/protected",
        expected_status_code=200,
        check_interval=60,
        auth_profile_id=profile.id,
    )

    monitor = asyncio.run(service.create_monitor(request))

    assert monitor.auth_profile_id == profile.id


class FakeAuthProfileServiceRepository:
    def __init__(self):
        self.profile = None

    async def get_by_name(self, name):
        return None

    async def create(self, profile):
        self.profile = profile
        return "507f1f77bcf86cd799439011"


def test_auth_profile_response_never_exposes_credential_values():
    repository = FakeAuthProfileServiceRepository()
    service = AuthProfileService(repository)
    request = CreateAuthProfileRequest(
        name="Service login",
        login_url="https://service.test/login",
        credentials={"username": "monitor", "password": "secret"},
    )

    profile = asyncio.run(service.create_profile(request))
    response = service.to_response(profile).model_dump()

    assert response["credential_fields"] == ["password", "username"]
    assert "credentials" not in response
    assert "secret" not in str(response)
