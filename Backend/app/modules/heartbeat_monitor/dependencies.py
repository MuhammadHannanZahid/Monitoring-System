from fastapi import Depends
from app.core.database import get_database

from app.modules.heartbeat_monitor.service import (
    HeartbeatMonitorRepository,
    HeartbeatMonitorService,
)


def get_heartbeat_repository(
    database=Depends(get_database),
) -> HeartbeatMonitorRepository:
    return HeartbeatMonitorRepository(database)


def get_heartbeat_service(
    repository: HeartbeatMonitorRepository = Depends(get_heartbeat_repository),
) -> HeartbeatMonitorService:
    return HeartbeatMonitorService(repository)
