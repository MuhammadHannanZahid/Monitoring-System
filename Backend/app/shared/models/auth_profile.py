from datetime import datetime

from pydantic import BaseModel, Field


class AuthProfileModel(BaseModel):
    id: str | None = None
    name: str
    login_url: str
    method: str = "POST"
    credentials: dict[str, str]
    headers: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
