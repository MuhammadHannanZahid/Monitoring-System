from fastapi import Depends
import app.modules.monitor.scheduler as scheduler_state
from app.modules.insight_manager.service import DashboardService
from app.modules.monitoring_controller.service import MonitorService

def get_monitor_service() -> MonitorService:
    if scheduler_state.scheduler is None:
        raise RuntimeError("The monitor scheduler has not been initialized.")
    return scheduler_state.scheduler.monitor_service

def get_dashboard_service(monitor_service: MonitorService = Depends(get_monitor_service)) -> DashboardService:
    return DashboardService(
        monitor_service=monitor_service,
        monitor_result_service=monitor_service.monitor_result_service,
        incident_service=monitor_service.incident_service,
    )