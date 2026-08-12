from fastapi import Depends
from odmantic import AIOEngine
from app.service.mongo_db.mongo_controller import get_engine
from app.modules.http_monitor_manager.service import HTTP_monitorService

def get_HTTP_monitor_service(engine: AIOEngine = Depends(get_engine)) -> HTTP_monitorService:
    return HTTP_monitorService(engine)
