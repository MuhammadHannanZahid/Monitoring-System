from dataclasses import dataclass
from app.shared.models.auth_user import UserRole

@dataclass(slots=True)
class AuthTokens:
    access_token: str
    refresh_token: str

@dataclass(slots=True)
class CurrentUser:
    id: str
    username: str
    role: UserRole
