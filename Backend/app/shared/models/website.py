from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field
from app.shared.enums import WebsiteStatus

class WebsiteModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    id: str | None = None
    name: str
    url: str
    check_interval: int
    expected_status_code: int
    timeout: int
    is_active: bool = True
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    last_checked_at: datetime | None = None
    last_status_code: int | None = None
    last_response_time_ms: int | None = None
    status: WebsiteStatus = WebsiteStatus.UNKNOWN
    failure_count: int = 0
    success_count: int = 0

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))