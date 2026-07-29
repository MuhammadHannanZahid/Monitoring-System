from app.modules.monitor.service import MonitorService
from fastapi import Depends
from app.modules.website.repository import WebsiteRepository, get_website_repository

def get_monitor_service(repository: WebsiteRepository = Depends(get_website_repository)) -> MonitorService:
    return MonitorService(repository)