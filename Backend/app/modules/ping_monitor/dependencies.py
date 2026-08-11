from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.modules.ping_monitor.service import PingMonitorRepository, PingMonitorService

def get_ping_repository(
    engine: AIOEngine = Depends(get_engine),
) -> PingMonitorRepository:
    return PingMonitorRepository(engine)

def get_ping_service(repository: PingMonitorRepository = Depends(get_ping_repository)) -> PingMonitorService:
    return PingMonitorService(repository)
