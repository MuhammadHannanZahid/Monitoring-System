import time
import httpx
from app.core.config import settings
from app.core.logger import get_logger
from app.modules.API_monitor.json_matcher import json_matches
from app.modules.monitor.schemas import HealthCheckResponse
from app.shared.enums import MonitorStatus

logger = get_logger(__name__)


class ApiChecker:

    def __init__(self):
        self.client = httpx.AsyncClient(follow_redirects=True)

    async def check(self, monitor) -> HealthCheckResponse:

        start = time.perf_counter()

        status = MonitorStatus.DOWN
        success = False
        status_code = None
        response_time_ms = None

        try:
            response = await self.client.request(
                method=monitor.method,
                url=monitor.url,
                timeout=settings.DEFAULT_TIMEOUT,
                headers=monitor.headers or {},
                json=monitor.request_body or None,
            )

            elapsed = int((time.perf_counter() - start) * 1000)

            status_code = response.status_code
            response_time_ms = elapsed

            # ----------------------------
            # Status code validation
            # ----------------------------
            status_ok = (
                response.status_code ==
                monitor.expected_status_code
            )

            # ----------------------------
            # JSON validation
            # ----------------------------
            response_json = None

            try:
                response_json = response.json()

            except ValueError:
                response_json = None

            if monitor.expected_json:
                json_ok = json_matches(
                    monitor.expected_json,
                    response_json,
                )
            else:
                json_ok = True

            headers_ok = True

            if monitor.expected_headers:

                for key, expected in monitor.expected_headers.items():

                    actual = response.headers.get(key)

                    if actual != expected:
                        headers_ok = False
                        break

            content_type_ok = True

            if monitor.expected_content_type:
                actual = response.headers.get(
                    "Content-Type",
                    "",
                )

                content_type_ok = (
                        monitor.expected_content_type.lower()
                        in actual.lower()
                )

            response_time_ok = (
                    monitor.expected_response_time_ms is None
                    or elapsed <= monitor.expected_response_time_ms
            )

            success = (
                    status_ok
                    and json_ok
                    and headers_ok
                    and content_type_ok
                    and response_time_ok
            )

            status = (
                MonitorStatus.UP
                if success
                else MonitorStatus.DOWN
            )

            if success:

                logger.info(
                    "[%s] '%s' is UP (%d ms, HTTP %d)",
                    monitor.method,
                    monitor.name,
                    elapsed,
                    response.status_code,
                )

            else:

                if not status_ok:

                    logger.warning(
                        "[%s] '%s' is DOWN (expected %d, got %d)",
                        monitor.method,
                        monitor.name,
                        monitor.expected_status_code,
                        response.status_code,
                    )

                elif not json_ok:

                    logger.warning(
                        "API Monitor '%s' failed JSON validation.",
                        monitor.name,
                    )

                elif not headers_ok:

                    logger.warning(
                        "API Monitor '%s' failed response header validation.",
                        monitor.name,
                    )

                elif not content_type_ok:

                    logger.warning(
                        "API Monitor '%s' returned wrong Content-Type.",
                        monitor.name,
                    )

                elif not response_time_ok:

                    logger.warning(
                        "API Monitor '%s' exceeded expected response time.",
                        monitor.name,
                    )

        except httpx.TimeoutException:

            response_time_ms = int(
                (time.perf_counter() - start) * 1000
            )

            logger.warning(
                "API Monitor '%s' timed out.",
                monitor.name,
            )

        except httpx.HTTPError as exc:

            response_time_ms = int(
                (time.perf_counter() - start) * 1000
            )

            logger.warning(
                "API Monitor '%s' failed: %s",
                monitor.name,
                exc,
            )

        except Exception:

            logger.exception(
                "Unexpected error while checking API monitor '%s'.",
                monitor.name,
            )

        return HealthCheckResponse(
            url=monitor.url,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            success=success,
        )

    async def close(self):
        await self.client.aclose()