from dataclasses import dataclass
from app.shared.models.website import WebsiteModel

@dataclass(slots=True)
class WebsiteResult:
    website: WebsiteModel