from fastapi import Depends
from app.modules.dashboard.service import DashboardService
from app.modules.website.dependencies import get_website_repository
from app.modules.monitor_results.dependencies import get_monitor_result_repository
from app.modules.incident.dependencies import get_incident_repository
from app.modules.website.repository import WebsiteRepository, get_website_repository
from app.modules.monitor_results.repository import MonitorResultRepository, get_monitor_result_repository
from app.modules.incident.repository import IncidentRepository, get_incident_repository

def get_dashboard_service(
    website_repository: WebsiteRepository = Depends(get_website_repository),
    monitor_result_repository: MonitorResultRepository = Depends(get_monitor_result_repository),
    incident_repository: IncidentRepository = Depends(get_incident_repository)) -> DashboardService:

    return DashboardService(
        website_repository=website_repository,
        monitor_result_repository=monitor_result_repository,
        incident_repository=incident_repository,
    )