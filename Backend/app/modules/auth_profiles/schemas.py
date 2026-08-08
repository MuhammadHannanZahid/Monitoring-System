from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateAuthProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    login_url: str = Field(min_length=1, max_length=500)
    method: str = Field(default="POST", min_length=1, max_length=10)
    credentials: dict[str, str] = Field(min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    credential_location: Literal["json", "form"] = "json"
    token_field: str = Field(default="access_token", min_length=1, max_length=200)
    expires_in_field: str | None = Field(
        default="expires_in",
        min_length=1,
        max_length=200,
    )


class UpdateAuthProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    login_url: str | None = Field(default=None, min_length=1, max_length=500)
    method: str | None = Field(default=None, min_length=1, max_length=10)
    credentials: dict[str, str] | None = Field(default=None, min_length=1)
    headers: dict[str, str] | None = None
    credential_location: Literal["json", "form"] | None = None
    token_field: str | None = Field(default=None, min_length=1, max_length=200)
    expires_in_field: str | None = Field(default=None, min_length=1, max_length=200)


class AuthProfileResponse(BaseModel):
    id: str
    name: str
    login_url: str
    method: str
    credential_fields: list[str]
    credential_location: Literal["json", "form"]
    token_field: str
    expires_in_field: str | None
    created_at: datetime
    updated_at: datetime
