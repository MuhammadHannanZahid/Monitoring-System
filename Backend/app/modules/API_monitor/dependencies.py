from fastapi import Depends
from app.core.database import get_database
from app.modules.api_monitor.repository import ApiMonitorRepository
from app.modules.api_monitor.service import ApiMonitorService

def get_api_monitor_service(database=Depends(get_database)):
    repository = ApiMonitorRepository(database)
    return ApiMonitorService(repository)