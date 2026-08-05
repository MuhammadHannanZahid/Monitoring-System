import httpx
import time
from app.core.logger import get_logger
from app.modules.monitor.schemas import HealthCheckResponse
from app.shared.enums import MonitorStatus
from app.shared.models.HTTP_monitor import HTTPMonitorModel
from .base_checker import BaseChecker
from app.core.config import settings

logger = get_logger(__name__)

class HTTPChecker(BaseChecker):
    def __init__(self):
        self.client = httpx.AsyncClient(follow_redirects=True)

    async def check(self, HTTP_monitor: HTTPMonitorModel) -> HealthCheckResponse:
        start = time.perf_counter()
        status = MonitorStatus.DOWN
        success = False
        status_code = None
        response_time_ms = None
        is_slow = False

        try:
            response = await self.client.get(HTTP_monitor.url, timeout=settings.default_timeout)
            elapsed = int((time.perf_counter() - start) * 1000)
            status_code = response.status_code
            response_time_ms = elapsed
            is_slow = False

            if HTTP_monitor.expected_response_time_ms is not None and elapsed > HTTP_monitor.expected_response_time_ms:
                is_slow = True

            status_ok = response.status_code == HTTP_monitor.expected_status_code

            is_slow = HTTP_monitor.expected_response_time_ms is not None and elapsed > HTTP_monitor.expected_response_time_ms

            success = status_ok
            status = MonitorStatus.UP if success else MonitorStatus.DOWN

            if success:
                if is_slow:
                    logger.warning("Monitor '%s' is UP but SLOW (%d ms > %d ms).", HTTP_monitor.name, elapsed, HTTP_monitor.expected_response_time_ms)
                else:
                    logger.info("Monitor '%s' is UP (%d ms, HTTP %d).", HTTP_monitor.name, elapsed, response.status_code)
            else:
                logger.warning("Monitor '%s' is DOWN (expected HTTP %d, got %d).", HTTP_monitor.name, HTTP_monitor.expected_status_code, response.status_code)
        except httpx.TimeoutException:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check timed out for '%s'.", HTTP_monitor.name)

        except httpx.HTTPError as exc:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check failed for '%s': %s", HTTP_monitor.name, exc)

        except Exception:
            logger.exception("Unexpected error while checking '%s'.", HTTP_monitor.name)

        return HealthCheckResponse(
            url=HTTP_monitor.url,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            success=success,
            is_slow=is_slow,
        )

    async def close(self):
        await self.client.aclose()