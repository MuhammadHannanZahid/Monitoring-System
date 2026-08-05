from dataclasses import dataclass
from app.shared.models.HTTP_monitor import HTTP_monitorModel

@dataclass(slots=True)
class HTTP_monitorResult:
    HTTP_monitor: HTTP_monitorModel