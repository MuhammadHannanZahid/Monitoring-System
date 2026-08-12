from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.modules.heartbeat_monitor.service import HeartbeatMonitorService


def get_heartbeat_service(
    engine: AIOEngine = Depends(get_engine),
) -> HeartbeatMonitorService:
    return HeartbeatMonitorService(engine)
