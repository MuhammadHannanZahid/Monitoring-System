from fastapi import Depends

import app.core.scheduler as scheduler_state
from app.modules.dashboard.service import DashboardService
from app.modules.monitor.service import MonitorService
from app.modules.monitor_results.service import MonitorResultRepository, get_monitor_result_repository
from app.modules.incident.service import IncidentRepository, get_incident_repository


def get_monitor_service() -> MonitorService:
    if scheduler_state.scheduler is None:
        raise RuntimeError("The monitor scheduler has not been initialized.")
    return scheduler_state.scheduler.monitor_service

def get_dashboard_service(
    monitor_service: MonitorService = Depends(get_monitor_service),
    incident_repository: IncidentRepository = Depends(get_incident_repository),
    monitor_result_repository: MonitorResultRepository = Depends(get_monitor_result_repository)
) -> DashboardService:
    return DashboardService(
        monitor_service=monitor_service,
        monitor_result_repository=monitor_result_repository,
        incident_repository=incident_repository,
    )
