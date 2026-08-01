from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field
from app.shared.enums import HTTP_monitorStatus

class ApiMonitorModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    id: str | None = None
    name: str
    url: str
    method: str
    headers: dict[str, str] = {}
    request_body: dict | None = None
    expected_status_code: int
    expected_json: dict | None = None
    timeout: int
    check_interval: int
    is_active: bool = True
    created_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_checked_at: datetime | None = None
    last_status_code: int | None = None
    last_response_time_ms: int | None = None
    status: HTTP_monitorStatus = HTTP_monitorStatus.UNKNOWN