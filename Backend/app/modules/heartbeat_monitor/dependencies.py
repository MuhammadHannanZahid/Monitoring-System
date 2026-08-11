from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine

from app.modules.heartbeat_monitor.service import (
    HeartbeatMonitorRepository,
    HeartbeatMonitorService,
)


def get_heartbeat_repository(
    engine: AIOEngine = Depends(get_engine),
) -> HeartbeatMonitorRepository:
    return HeartbeatMonitorRepository(engine)


def get_heartbeat_service(
    repository: HeartbeatMonitorRepository = Depends(get_heartbeat_repository),
) -> HeartbeatMonitorService:
    return HeartbeatMonitorService(repository)
