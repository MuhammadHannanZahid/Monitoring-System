from fastapi import Depends
from odmantic import AIOEngine
from app.service.mongo_db.mongo_controller import get_engine
from app.modules.ping_monitor_manager.service import PingMonitorService

def get_ping_service(engine: AIOEngine = Depends(get_engine)) -> PingMonitorService:
    return PingMonitorService(engine)
