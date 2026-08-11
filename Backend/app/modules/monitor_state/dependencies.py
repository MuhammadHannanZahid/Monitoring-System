from fastapi import Depends
from odmantic import AIOEngine

from app.core.database import get_engine
from app.modules.monitor_state.service import MonitorStateRepository, MonitorStateService

def get_monitor_state_service(engine: AIOEngine = Depends(get_engine)):
    repository = MonitorStateRepository(engine)
    return MonitorStateService(repository)
