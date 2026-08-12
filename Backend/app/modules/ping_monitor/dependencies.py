from fastapi import Depends
from odmantic import AIOEngine
from app.core.database import get_engine
from app.modules.ping_monitor.service import PingMonitorService

def get_ping_service(engine: AIOEngine = Depends(get_engine)) -> PingMonitorService:
    return PingMonitorService(engine)
