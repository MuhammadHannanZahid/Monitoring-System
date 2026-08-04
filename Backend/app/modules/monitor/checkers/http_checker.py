import httpx
import time
from app.core.logger import get_logger
from app.modules.monitor.schemas import HealthCheckResponse
from app.shared.enums import MonitorStatus
from app.shared.models.HTTP_monitor import HTTPMonitorModel
from .base_checker import BaseChecker

logger = get_logger(__name__)

class HTTPChecker(BaseChecker):
    def __init__(self):
        self.client = httpx.AsyncClient(
            follow_redirects=True
        )

    async def check(self, HTTP_monitor: HTTPMonitorModel) -> HealthCheckResponse:
        start = time.perf_counter()

        status = MonitorStatus.DOWN
        success = False
        status_code = None
        response_time_ms = None
        try:
            response = await self.client.get(HTTP_monitor.url, timeout=HTTP_monitor.timeout)

            elapsed = int((time.perf_counter() - start) * 1000)
            status_code = response.status_code
            response_time_ms = elapsed
            status_ok = (
                    response.status_code
                    == HTTP_monitor.expected_status_code
            )

            response_time_ok = (
                    HTTP_monitor.expected_response_time_ms is None
                    or elapsed <= HTTP_monitor.expected_response_time_ms
            )

            success = status_ok and response_time_ok
            status = MonitorStatus.UP if success else MonitorStatus.DOWN

            if success:
                logger.info(
                    "Monitor '%s' is UP (%d ms, HTTP %d).",
                    HTTP_monitor.name,
                    elapsed,
                    response.status_code,
                )

            elif not status_ok:
                logger.warning(
                    "Monitor '%s' is DOWN (expected HTTP %d, got %d).",
                    HTTP_monitor.name,
                    HTTP_monitor.expected_status_code,
                    response.status_code,
                )

            elif not response_time_ok:
                logger.warning(
                    "Monitor '%s' is DOWN (response time %d ms exceeded limit %d ms).",
                    HTTP_monitor.name,
                    elapsed,
                    HTTP_monitor.expected_response_time_ms,
                )

        except httpx.TimeoutException:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check timed out for '%s'.", HTTP_monitor.name)

        except httpx.HTTPError as exc:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check failed for '%s' : %s", HTTP_monitor.name, exc)

        except Exception:
            logger.exception("Unexpected error while checking '%s'.", HTTP_monitor.name)

        return HealthCheckResponse(
            url=HTTP_monitor.url,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            success=success,
        )

    async def close(self):
        await self.client.aclose()