from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AuthProfileModel(BaseModel):
    id: str | None = None
    name: str
    login_url: str
    method: str = "POST"
    credentials: dict[str, str]
    headers: dict[str, str] = Field(default_factory=dict)
    credential_location: Literal["json", "form"] = "json"
    token_field: str = "access_token"
    expires_in_field: str | None = "expires_in"
    created_at: datetime
    updated_at: datetime
