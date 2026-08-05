from fastapi import Depends
from app.modules.dashboard.service import DashboardService
from app.modules.monitor_results.dependencies import get_monitor_result_repository
from app.modules.incident.dependencies import get_incident_repository
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository, get_HTTP_monitor_repository
from app.modules.monitor_results.repository import MonitorResultRepository, get_monitor_result_repository
from app.modules.incident.repository import IncidentRepository, get_incident_repository
from app.modules.API_monitor.repository import API_monitorRepository, get_API_monitor_repository

def get_dashboard_service(
    HTTP_monitor_repository: HTTP_monitorRepository = Depends(get_HTTP_monitor_repository),
    API_monitor_repository: API_monitorRepository = Depends(get_API_monitor_repository),
    incident_repository: IncidentRepository = Depends(get_incident_repository),
    monitor_result_repository: MonitorResultRepository = Depends(get_monitor_result_repository)
) -> DashboardService:
    return DashboardService(
        HTTP_monitor_repository=HTTP_monitor_repository,
        API_monitor_repository=API_monitor_repository,
        monitor_result_repository=monitor_result_repository,
        incident_repository=incident_repository,
    )