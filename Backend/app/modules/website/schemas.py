from datetime import datetime
from pydantic import BaseModel, Field

class CreateWebsiteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(max_length=500)

    check_interval: int = Field(ge=10, le=86400)
    expected_status_code: int = Field(ge=100, le=599)
    timeout: int = Field(ge=1, le=60)

class UpdateWebsiteRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, max_length=500)
    check_interval: int | None = Field(default=None, ge=10, le=86400)
    expected_status_code: int | None = Field(default=None, ge=100, le=599)
    timeout: int | None = Field(default=None, ge=1, le=60)
    is_active: bool | None = None

class WebsiteResponse(BaseModel):
    id: str
    name: str
    url: str
    check_interval: int
    expected_status_code: int
    timeout: int
    is_active: bool
    created_by: str |None = None
    created_at: datetime
    updated_at: datetime
    last_checked_at: datetime | None