import time
import httpx
from app.core.logger import get_logger
from app.modules.monitor.schemas import HealthCheckResponse
from app.shared.enums import WebsiteStatus
from app.modules.website.repository import WebsiteRepository
from app.modules.monitor_results.service import MonitorResultService
from app.modules.incident.service import IncidentService
from app.shared.models.website import WebsiteModel
from datetime import datetime, timezone

logger = get_logger(__name__)

class MonitorService:
    def __init__(
        self,
        website_repository: WebsiteRepository,
        incident_service: IncidentService,
        monitor_result_service: MonitorResultService,
    ):
        self.website_repository = website_repository
        self.incident_service = incident_service
        self.monitor_result_service = monitor_result_service

    async def check_website(self, website: WebsiteModel) -> HealthCheckResponse:
        start = time.perf_counter()

        status = WebsiteStatus.DOWN
        status_code = None
        response_time_ms = None
        success = False
        try:
            self.client = httpx.AsyncClient(follow_redirects=True)
            response = await self.client.get(website.url, timeout=website.timeout)

            elapsed = int((time.perf_counter() - start) * 1000)

            status_code = response.status_code
            response_time_ms = elapsed

            if response.status_code == website.expected_status_code:
                status = WebsiteStatus.UP
                success = True
            else:
                status = WebsiteStatus.DOWN
                success = False

            if success:
                logger.info("Website '%s' is UP (%d ms, HTTP %d).", website.name, elapsed, response.status_code)
            else:
                logger.warning("Website '%s' is DOWN (expected %d, got %d).", website.name, website.expected_status_code, response.status_code)

        except httpx.TimeoutException:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check timed out for '%s'.", website.name)

        except httpx.HTTPError as exc:
            response_time_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("Health check failed for '%s'", website.name)

        return HealthCheckResponse(
            url=website.url,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            success=success,
        )

    async def close(self):
        await self.client.aclose()

    async def check_and_update(self, website: WebsiteModel) -> HealthCheckResponse:
        previous_status = website.status
        result = await self.check_website(website)
        checked_at = datetime.now(timezone.utc)

        await self.monitor_result_service.record_result(
            website_id=website.id,
            status=result.status,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            success=result.success,
        )

        await self.website_repository.update_monitoring_result(
            website_id=website.id,
            status=result.status,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms,
            checked_at=checked_at,
        )

        logger.info("Health Check | Website='%s' | Status=%s | HTTP=%s | Response=%sms", website.name, result.status.value, result.status_code, result.response_time_ms)

        if previous_status != WebsiteStatus.DOWN and result.status == WebsiteStatus.DOWN:
            active = await self.incident_service.get_active_incident(website.id)

            if active is None:
                reason = (
                    f"HTTP {result.status_code}"
                    if result.status_code is not None
                    else "Timeout / Network Error")

                await self.incident_service.open_incident(website_id=website.id, reason=reason)
                logger.warning("Incident opened for website '%s'.", website.name)

        elif previous_status == WebsiteStatus.DOWN and result.status == WebsiteStatus.UP:
            await self.incident_service.resolve_incident(website.id)
            logger.info("Incident resolved for website '%s'.", website.name)

        return result