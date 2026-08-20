import asyncio
from types import SimpleNamespace

import httpx

from app.modules.monitoring_controller.checkers.api_checker import ApiChecker
from app.modules.monitoring_controller.checkers.http_checker import HTTPChecker
from app.modules.monitoring_controller.monitoring_controller import MonitorManager
from app.service.mongo_db.shared_models.db_monitoring_controller_model import (
    HealthCheckResponse,
    MonitorStatus,
    MonitorType,
)


def test_status_mismatch_includes_code_phrase_and_description() -> None:
    async def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    async def run_check() -> HealthCheckResponse:
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            checker = HTTPChecker(client=client)
            return await checker.check(
                SimpleNamespace(
                    name="404 test",
                    url="http://status-test/status/404",
                    timeout=5,
                    expected_status_code=200,
                    expected_response_time_ms=1000,
                )
            )

    result = asyncio.run(run_check())
    reason = MonitorManager._build_incident_reason(
        SimpleNamespace(
            monitor_type=MonitorType.HTTP,
            expected_status_code=200,
        ),
        result,
    )

    assert result.status_code == 404
    assert result.timed_out is False
    assert "Expected HTTP 200 OK" in reason
    assert "received HTTP 404 Not Found" in reason
    assert "Nothing matches the given URI" in reason


def test_elapsed_milliseconds_do_not_cause_false_timeout_reason() -> None:
    result = HealthCheckResponse(
        url="https://unreachable.invalid",
        status=MonitorStatus.DOWN,
        status_code=None,
        response_time_ms=5000,
        success=False,
        error="Could not connect to the target.",
        timed_out=False,
    )

    reason = MonitorManager._build_incident_reason(
        SimpleNamespace(
            monitor_type=MonitorType.HTTP,
            expected_status_code=200,
            timeout=5,
        ),
        result,
    )

    assert reason == "Could not connect to the target."


def test_actual_timeout_uses_explicit_timeout_flag() -> None:
    async def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("test timeout", request=request)

    async def run_check() -> HealthCheckResponse:
        async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
            checker = HTTPChecker(client=client)
            return await checker.check(
                SimpleNamespace(
                    name="timeout test",
                    url="https://example.test",
                    timeout=5,
                    expected_status_code=200,
                    expected_response_time_ms=1000,
                )
            )

    result = asyncio.run(run_check())
    reason = MonitorManager._build_incident_reason(
        SimpleNamespace(
            monitor_type=MonitorType.HTTP,
            expected_status_code=200,
        ),
        result,
    )

    assert result.timed_out is True
    assert reason == "The target did not complete its response within 5 seconds."


def test_api_response_validation_failure_keeps_returned_status() -> None:
    async def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"healthy": False}, request=request)

    async def run_check() -> HealthCheckResponse:
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            checker = ApiChecker(client=client)
            return await checker.check(
                SimpleNamespace(
                    name="JSON test",
                    method="GET",
                    url="https://example.test/health",
                    headers={},
                    request_body=None,
                    timeout=5,
                    auth_profile_id=None,
                    expected_status_code=200,
                    expected_json={"healthy": True},
                    expected_headers=None,
                    expected_content_type=None,
                    expected_response_time_ms=1000,
                )
            )

    result = asyncio.run(run_check())
    reason = MonitorManager._build_incident_reason(
        SimpleNamespace(
            monitor_type=MonitorType.API,
            expected_status_code=200,
        ),
        result,
    )

    assert result.status_code == 200
    assert result.error == "The response JSON did not match the configured expected JSON."
    assert "Received HTTP 200 OK" in reason
    assert "response JSON did not match" in reason


def test_status_without_runtime_description_uses_clear_fallback() -> None:
    result = HealthCheckResponse(
        url="https://example.test",
        status=MonitorStatus.DOWN,
        status_code=422,
        response_time_ms=20,
        success=False,
    )

    reason = MonitorManager._build_incident_reason(
        SimpleNamespace(
            monitor_type=MonitorType.HTTP,
            expected_status_code=200,
        ),
        result,
    )

    assert "HTTP 422 Unprocessable Entity" in reason
    assert "understood the request but could not process its content" in reason
