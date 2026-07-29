from fastapi import Depends
from app.core.database import get_database
from app.modules.website.repository import WebsiteRepository
from app.modules.website.repository import WebsiteRepository, get_website_repository
from app.modules.website.service import WebsiteService

def get_website_repository(database=Depends(get_database)) -> WebsiteRepository:
    return WebsiteRepository(database)

def get_website_service(repository: WebsiteRepository = Depends(get_website_repository)) -> WebsiteService:
    return WebsiteService(repository)