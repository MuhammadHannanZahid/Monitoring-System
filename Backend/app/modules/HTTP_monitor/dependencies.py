from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.modules.HTTP_monitor.service import HTTP_monitorService


def get_HTTP_monitor_service(
    engine: AIOEngine = Depends(get_engine),
) -> HTTP_monitorService:
    return HTTP_monitorService(engine)
