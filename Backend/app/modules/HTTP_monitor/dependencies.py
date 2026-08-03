from fastapi import Depends
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository, get_HTTP_monitor_repository
from app.modules.HTTP_monitor.service import HTTP_monitorService

# def get_HTTP_monitor_repository(database=Depends(get_database)) -> HTTP_monitorRepository:
#     return HTTP_monitorRepository(database)

def get_HTTP_monitor_service(repository: HTTP_monitorRepository = Depends(get_HTTP_monitor_repository)) -> HTTP_monitorService:
    return HTTP_monitorService(repository)