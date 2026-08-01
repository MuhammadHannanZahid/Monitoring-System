from fastapi import Depends
from app.core.database import get_database
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository, get_website_repository
from app.modules.HTTP_monitor.service import HTTP_monitorService

def get_website_repository(database=Depends(get_database)) -> HTTP_moniotrRepository:
    return HTTP_monitorRepository(database)

def get_website_service(repository: HTTP_monitorRepository = Depends(get_website_repository)) -> HTTP_monitorService:
    return HTTP_monitorService(repository)