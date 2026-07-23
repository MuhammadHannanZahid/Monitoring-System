from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.shared.enums import UserRole

class UserModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    id: str | None = None
    username: str
    password_hash: str
    role: UserRole
    refresh_token_hash: str | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None