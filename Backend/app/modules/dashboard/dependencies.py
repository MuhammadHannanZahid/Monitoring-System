from fastapi import Depends
from app.modules.dashboard.service import DashboardService
from app.modules.website.dependencies import get_website_repository
from app.modules.monitor_results.dependencies import get_monitor_result_repository
from app.modules.incidents.dependencies import get_incident_repository

def get_dashboard_service(
    website_repository=Depends(get_website_repository),
    monitor_result_repository=Depends(get_monitor_result_repository),
    incident_repository=Depends(get_incident_repository),
) -> DashboardService:
    return DashboardService(
        website_repository,
        monitor_result_repository,
        incident_repository,
    )