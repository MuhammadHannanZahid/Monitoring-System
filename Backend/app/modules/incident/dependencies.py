from fastapi import Depends
from app.modules.incident.service import (
    IncidentRepository,
    IncidentService,
    get_incident_repository,
)

def get_incident_service(repository: IncidentRepository = Depends(get_incident_repository)) -> IncidentService:
    return IncidentService(repository)
