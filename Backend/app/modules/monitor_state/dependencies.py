from fastapi import Depends
from app.core.database import get_database
from app.modules.monitor_state.repository import MonitorStateRepository
from app.modules.monitor_state.service import MonitorStateService

def get_monitor_state_service(database=Depends(get_database)):
    repository = MonitorStateRepository(database)
    return MonitorStateService(repository)