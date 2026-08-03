from fastapi import Depends
from app.modules.API_monitor.repository import API_monitorRepository, get_API_monitor_repository
from app.modules.API_monitor.service import API_monitorService

def get_API_monitor_service(repository: API_monitorRepository = Depends(get_API_monitor_repository)) -> API_monitorService:
    return API_monitorService(repository)