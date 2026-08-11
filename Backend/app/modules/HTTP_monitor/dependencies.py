from fastapi import Depends
from app.modules.HTTP_monitor.service import (
    HTTP_monitorRepository,
    HTTP_monitorService,
    get_HTTP_monitor_repository,
)

def get_HTTP_monitor_service(repository: HTTP_monitorRepository = Depends(get_HTTP_monitor_repository)) -> HTTP_monitorService:
    return HTTP_monitorService(repository)
