from app.modules.dashboard.schemas import DashboardSummaryResponse
from app.shared.enums import WebsiteStatus

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