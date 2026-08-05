from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.modules.ping_monitor.repository import PingMonitorRepository
from app.modules.ping_monitor.service import PingMonitorService

def get_ping_repository(database: AsyncIOMotorDatabase = Depends(get_database)) -> PingMonitorRepository:
    return PingMonitorRepository(database)

def get_ping_service(repository: PingMonitorRepository = Depends(get_ping_repository)) -> PingMonitorService:
    return PingMonitorService(repository)