from fastapi import Depends
from app.modules.incident.repository import IncidentRepository, get_incident_repository
from app.modules.incident.service import IncidentService

def get_incident_service(repository: IncidentRepository = Depends(get_incident_repository)) -> IncidentService:
    return IncidentService(repository)