from datetime import datetime
from pydantic import BaseModel, ConfigDict

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
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_checked_at: datetime | None = None