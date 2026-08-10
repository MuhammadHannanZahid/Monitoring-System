from datetime import datetime

from pydantic import BaseModel, Field


class CreateAuthProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    login_url: str = Field(min_length=1, max_length=500)
    method: str = Field(default="POST", min_length=1, max_length=10)
    credentials: dict[str, str] = Field(min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)


class UpdateAuthProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    login_url: str | None = Field(default=None, min_length=1, max_length=500)
    method: str | None = Field(default=None, min_length=1, max_length=10)
    credentials: dict[str, str] | None = Field(default=None, min_length=1)
    headers: dict[str, str] | None = None


class AuthProfileResponse(BaseModel):
    id: str
    name: str
    login_url: str
    method: str
    credential_fields: list[str]
    created_at: datetime
    updated_at: datetime
