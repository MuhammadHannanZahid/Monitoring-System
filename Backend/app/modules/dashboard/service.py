from app.shared.enums import WebsiteStatus
from app.modules.dashboard.schemas import (DashboardSummaryResponse, DashboardWebsiteResponse, DashboardIncidentResponse,
    DashboardActivityResponse, ResponseHistoryResponse, ResponseHistoryPoint, UptimeResponse, StatusHistoryResponse,
    StatusHistoryPoint)
from app.shared.exceptions import NotFoundError
from app.shared.constants import Messages
from app.modules.website.repository import WebsiteRepository
from app.modules.monitor_results.repository import MonitorResultRepository
from app.modules.incident.repository import IncidentRepository

class DashboardService:
    def __init__(self, website_repository: WebsiteRepository, monitor_result_repository: MonitorResultRepository, incident_repository: IncidentRepository):
        self.website_repository = website_repository
        self.monitor_result_repository = monitor_result_repository
        self.incident_repository = incident_repository

    async def get_summary(self) -> DashboardSummaryResponse:
        total_websites = await self.website_repository.count_all()
        active_websites = await self.website_repository.count_active()
        inactive_websites = await self.website_repository.count_inactive()
        websites_up = await self.website_repository.count_by_status(WebsiteStatus.UP)
        websites_down = await self.website_repository.count_by_status(WebsiteStatus.DOWN)
        websites_unknown = await self.website_repository.count_by_status(WebsiteStatus.UNKNOWN)
        open_incidents = await self.incident_repository.count_open()
        average_response_time = (await self.monitor_result_repository.average_response_time())

        return DashboardSummaryResponse(
            total_websites=total_websites,
            active_websites=active_websites,
            inactive_websites=inactive_websites,
            websites_up=websites_up,
            websites_down=websites_down,
            websites_unknown=websites_unknown,
            open_incidents=open_incidents,
            average_response_time_ms=average_response_time,
        )

    async def get_websites(self) -> list[DashboardWebsiteResponse]:
        websites = await self.website_repository.list_websites()

        responses = []

        for website in websites:
            stats = await self.monitor_result_repository.get_statistics(
                website_id=website.id,
                days=30,
            )

            total = stats["total"]
            successful = stats["successful"]

            uptime = (
                round(successful / total * 100, 2)
                if total > 0
                else 0.0
            )

            incidents = len(
                await self.incident_repository.list_by_website(website.id)
            )

            responses.append(
                DashboardWebsiteResponse(
                    id=website.id,
                    name=website.name,
                    url=website.url,
                    status=website.status,
                    response_time_ms=website.last_response_time_ms,
                    status_code=website.last_status_code,
                    uptime_percentage=uptime,
                    incidents=incidents,
                    last_checked_at=website.last_checked_at,
                    is_active=website.is_active,
                )
            )

        return responses

    async def get_recent_incidents(self) -> list[DashboardIncidentResponse]:
        incidents = await self.incident_repository.get_recent()
        websites = await self.website_repository.list_websites()
        website_map = {
            website.id: website
            for website in websites
        }

        results = []
        for incident in incidents:
            website = website_map.get(incident.website_id)

            results.append(
                DashboardIncidentResponse(
                    id=incident.id,
                    website_id=incident.website_id,
                    website_name=website.name if website else "Unknown",
                    started_at=incident.started_at,
                    resolved_at=incident.resolved_at,
                    duration_seconds=incident.duration_seconds,
                )
            )

        return results

    async def get_recent_activity(self) -> list[DashboardActivityResponse]:
        results = await self.monitor_result_repository.get_recent()
        websites = await self.website_repository.list_websites()

        website_map = {
            website.id: website
            for website in websites
        }

        activities = []
        for result in results:
            website = website_map.get(result.website_id)

            activities.append(
                DashboardActivityResponse(
                    website_name=website.name if website else "Unknown",
                    status=result.status,
                    status_code=result.status_code,
                    response_time_ms=result.response_time_ms,
                    checked_at=result.checked_at,
                )
            )

        return activities

    async def get_response_history(self, website_id: str, days: int) -> ResponseHistoryResponse:
        website = await self.website_repository.get_by_id(website_id)

        if website is None:
            raise NotFoundError(Messages.WEBSITE_NOT_FOUND)

        history = await self.monitor_result_repository.get_response_history(website_id=website_id, days=days)

        return ResponseHistoryResponse(
            website_id=website_id,
            points=[
                ResponseHistoryPoint(
                    checked_at=result.checked_at,
                    response_time_ms=result.response_time_ms,
                )
                for result in history
            ],
        )

    async def get_uptime(self, website_id: str, days: int) -> UptimeResponse:
        website = await self.website_repository.get_by_id(website_id)

        if website is None:
            raise NotFoundError(Messages.WEBSITE_NOT_FOUND)

        stats = await self.monitor_result_repository.get_statistics(website_id=website_id, days=days)
        total = stats["total"]
        successful = stats["successful"]
        failed = total - successful
        uptime = (round(successful / total * 100, 2) if total > 0 else 0.0)

        return UptimeResponse(
            website_id=website_id,
            uptime_percentage=uptime,
            total_checks=total,
            successful_checks=successful,
            failed_checks=failed,
        )

    async def get_status_history(self, website_id: str, days: int) -> StatusHistoryResponse:
        website = await self.website_repository.get_by_id(website_id)

        if website is None:
            raise NotFoundError(Messages.WEBSITE_NOT_FOUND)

        history = await self.monitor_result_repository.get_status_history(website_id=website_id, days=days)

        return StatusHistoryResponse(
            website_id=website_id,
            history=[
                StatusHistoryPoint(
                    checked_at=result.checked_at,
                    status=result.status,
                )
                for result in history
            ],
        )