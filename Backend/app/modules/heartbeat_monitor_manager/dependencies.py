from fastapi import Depends
from odmantic import AIOEngine
from app.service.mongo_db.mongo_controller import get_engine
from app.modules.heartbeat_monitor_manager.service import HeartbeatMonitorService

def get_heartbeat_service(engine: AIOEngine = Depends(get_engine)) -> HeartbeatMonitorService:
    return HeartbeatMonitorService(engine)
