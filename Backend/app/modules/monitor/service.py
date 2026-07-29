import time
import httpx
from app.core.logger import get_logger
from app.modules.monitor.schemas import HealthCheckResponse
from app.shared.enums import WebsiteStatus

logger = get_logger(__name__)

class MonitorService:
    def __init__(self, repository: WebsiteRepository):
        self.repository = repository

    async def check_website(website: WebsiteModel) -> HealthCheckResponse:
        start = time.perf_counter()

        status = WebsiteStatus.DOWN
        status_code = None
        response_time_ms = None
        success = False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(website.url, timeout=website.timeout)

            elapsed = int((time.perf_counter() - start) * 1000)

            if response.status_code == website.expected_status_code:
                status = WebsiteStatus.UP
                success = True
            else:
                status = WebsiteStatus.DOWN
                success = False

            if success:
                logger.info("Website '%s' is UP (%d ms, HTTP %d).", website.name, elapsed, response.status_code)
            else:
                logger.warning("Website '%s' is DOWN (expected %d, got %d).", website.name, expected_status_code, response.status_code)

        except httpx.TimeoutException:
            logger.warning("Health check timed out for '%s'.", website.name)

        except httpx.HTTPError as exc:
            logger.warning("Health check failed for '%s': %s", website.name, str(exc))

        return HealthCheckResponse(
            url=website.url,
            status=status,
            status_code=website.status_code,
            response_time_ms=response_time_ms,
            success=success,
        )

    async def check_and_update(self, website: WebsiteModel) -> HealthCheckResponse:
        result = await self.check_website(website)
        await self.repository.update_monitoring_result(
            website_id=website.id,
            status=result.status,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            checked_at=datetime.now(timezone.utc),
        )

        return result