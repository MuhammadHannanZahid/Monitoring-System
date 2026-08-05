from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.shared.enums import UserRole

class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    role: UserRole

class UpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=8)
    role: UserRole | None = None
    is_active: bool | None = None

class UserResponse(BaseModel):
    id: str
    username: str
    role: UserRole
    is_active: bool

    created_at: datetime
    updated_at: datetime
    last_login: datetime | None