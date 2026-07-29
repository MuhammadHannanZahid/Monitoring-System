import time
import httpx
from app.core.logger import get_logger
from app.modules.monitor.schemas import HealthCheckResponse
from app.shared.enums import WebsiteStatus

logger = get_logger(__name__)

class MonitorService:
    async def check_website(self, url: str, timeout: int, expected_status_code: int) -> HealthCheckResponse:
        start = time.perf_counter()

        status = WebsiteStatus.DOWN
        status_code = None
        response_time_ms = None
        success = False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=timeout)

            elapsed = int((time.perf_counter() - start) * 1000)

            if response.status_code == expected_status_code:
                status = WebsiteStatus.UP
                success = True
            else:
                status = WebsiteStatus.DOWN
                success = False

            if success:
                logger.info("Website '%s' is UP (%d ms, HTTP %d).", url, elapsed, response.status_code)
            else:
                logger.warning("Website '%s' is DOWN (expected %d, got %d).", url, expected_status_code, response.status_code)

        except httpx.TimeoutException:
            logger.warning("Health check timed out for '%s'.", url)

        except httpx.HTTPError as exc:
            logger.warning("Health check failed for '%s': %s", url, str(exc))

        return HealthCheckResponse(
            url=url,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            success=success,
        )