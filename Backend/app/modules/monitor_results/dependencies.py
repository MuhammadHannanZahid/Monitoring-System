from fastapi import Depends
from app.modules.monitor_results.repository import MonitorResultRepository, get_monitor_result_repository
from app.modules.monitor_results.service import MonitorResultService

def get_monitor_result_service(repository: MonitorResultRepository = Depends(get_monitor_result_repository)) -> MonitorResultService:
    return MonitorResultService(repository)