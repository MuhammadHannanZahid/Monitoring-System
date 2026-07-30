from app.modules.dashboard.schemas import DashboardSummaryResponse
from app.shared.enums import WebsiteStatus
from app.modules.dashboard.schemas import DashboardWebsiteResponse, DashboardIncidentResponse, DashboardActivityResponse

class DashboardService:
    def __init__(self, website_repository, monitor_result_repository, incident_repository):
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
        return [
            DashboardWebsiteResponse(
                id=website.id,
                name=website.name,
                url=website.url,
                status=website.status,
                response_time_ms=website.last_response_time_ms,
                last_checked_at=website.last_checked_at,
                is_active=website.is_active,
            )
            for website in websites
        ]

    async def get_recent_incidents(self) -> list[DashboardIncidentResponse]:
        incidents = await self.incident_repository.get_recent()

        results = []
        for incident in incidents:
            website = await self.website_repository.get_by_id(incident.website_id)

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

        activities = []
        for result in results:
            website = await self.website_repository.get_by_id(result.website_id)

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

