from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.modules.ping_monitor.repository import PingMonitorRepository

def get_ping_monitor_repository(database: AsyncIOMotorDatabase = Depends(get_database)) -> PingMonitorRepository:
    return PingMonitorRepository(database)