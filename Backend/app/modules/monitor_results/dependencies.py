from fastapi import Depends
from app.modules.monitor_results.repository import MonitorResultRepository, get_monitor_result_repository
from app.modules.monitor_results.service import MonitorResultService
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database

def get_monitor_result_service(repository: MonitorResultRepository = Depends(get_monitor_result_repository)) -> MonitorResultService:
    return MonitorResultService(repository)

def get_monitor_result_repository(database: AsyncIOMotorDatabase = Depends(get_database)) -> MonitorResultRepository:
    return MonitorResultRepository(database)