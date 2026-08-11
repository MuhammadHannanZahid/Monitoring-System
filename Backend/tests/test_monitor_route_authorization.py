from fastapi.routing import APIRoute

from app.modules.API_monitor.router import router as api_monitor_router
from app.modules.auth.dependencies import get_current_user
from app.modules.heartbeat_monitor.router import router as heartbeat_monitor_router


def dependency_calls(route: APIRoute) -> set[object]:
    calls = set()
    pending = list(route.dependant.dependencies)

    while pending:
        dependency = pending.pop()
        calls.add(dependency.call)
        pending.extend(dependency.dependencies)

    return calls


def api_routes(router) -> list[APIRoute]:
    return [route for route in router.routes if isinstance(route, APIRoute)]


def test_all_api_monitor_routes_require_an_authenticated_user():
    routes = api_routes(api_monitor_router)

    assert routes
    assert all(get_current_user in dependency_calls(route) for route in routes)


def test_all_heartbeat_management_routes_require_an_authenticated_user():
    management_routes = [
        route
        for route in api_routes(heartbeat_monitor_router)
        if route.path != "/heartbeat-monitors/heartbeat/{token}"
    ]

    assert management_routes
    assert all(
        get_current_user in dependency_calls(route)
        for route in management_routes
    )


def test_heartbeat_receiver_uses_its_monitor_token_instead_of_user_auth():
    receiver = next(
        route
        for route in api_routes(heartbeat_monitor_router)
        if route.path == "/heartbeat-monitors/heartbeat/{token}"
    )

    assert get_current_user not in dependency_calls(receiver)
    assert receiver.include_in_schema is False
