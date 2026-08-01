from dataclasses import dataclass
from app.shared.models.HTTP_monitor import WebsiteModel

@dataclass(slots=True)
class WebsiteResult:
    website: WebsiteModel