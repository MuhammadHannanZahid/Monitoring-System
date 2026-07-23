from pydantic import BaseModel, Field
from app.shared.enums import UserRole
from typing import Literal

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"] = "Bearer"

class CurrentUserResponse(BaseModel):
    id: str
    username: str
    role: UserRole