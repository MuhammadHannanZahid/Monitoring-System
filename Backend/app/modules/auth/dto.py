from dataclasses import dataclass

@dataclass(slots=True)
class AuthTokens:
    access_token: str
    refresh_token: str
