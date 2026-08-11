from fastapi import Depends
from app.modules.monitor_results.service import (
    MonitorResultRepository,
    MonitorResultService,
    get_monitor_result_repository,
)

def get_monitor_result_service(repository: MonitorResultRepository = Depends(get_monitor_result_repository)) -> MonitorResultService:
    return MonitorResultService(repository)
