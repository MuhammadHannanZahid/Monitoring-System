from app.modules.monitor.service import MonitorService
from fastapi import Depends
from app.modules.website.repository import WebsiteRepository
from app.modules.incident.dependencies import get_incident_service
from app.modules.incident.service import IncidentService
from app.modules.website.dependencies import get_website_repository
from app.modules.monitor_results.dependencies import get_monitor_result_service
from app.modules.monitor_results.service import MonitorResultService

def get_monitor_service(website_repository: WebsiteRepository = Depends(get_website_repository), incident_service: IncidentService = Depends(get_incident_service), monitor_result_service: MonitorResultService = Depends(get_monitor_result_service)) -> MonitorService:
    return MonitorService(
        website_repository=website_repository,
        incident_service=incident_service,
        monitor_result_service=monitor_result_service,
    )