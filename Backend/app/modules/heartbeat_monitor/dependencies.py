from fastapi import Depends
from app.core.database import get_database

from app.modules.heartbeat_monitor.repository import HeartbeatMonitorRepository
from app.modules.heartbeat_monitor.service import HeartbeatMonitorService


def get_heartbeat_repository(
    database=Depends(get_database),
) -> HeartbeatMonitorRepository:
    return HeartbeatMonitorRepository(database)


def get_heartbeat_service(
    repository: HeartbeatMonitorRepository = Depends(get_heartbeat_repository),
) -> HeartbeatMonitorService:
    return HeartbeatMonitorService(repository)