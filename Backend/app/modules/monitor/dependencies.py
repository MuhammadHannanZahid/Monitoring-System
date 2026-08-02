from app.modules.monitor.service import MonitorService
from fastapi import Depends
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.modules.incident.dependencies import get_incident_service
from app.modules.incident.service import IncidentService
from app.modules.HTTP_monitor.dependencies import get_HTTP_monitor_repository
from app.modules.monitor_results.dependencies import get_monitor_result_service
from app.modules.monitor_results.service import MonitorResultService

def get_monitor_service(HTTP_monitor_repository: HTTP_monitorRepository = Depends(get_HTTP_monitor_repository), incident_service: IncidentService = Depends(get_incident_service), monitor_result_service: MonitorResultService = Depends(get_monitor_result_service)) -> MonitorService:
    return MonitorService(
        HTTP_monitor_repository=HTTP_monitor_repository,
        incident_service=incident_service,
        monitor_result_service=monitor_result_service,
    )