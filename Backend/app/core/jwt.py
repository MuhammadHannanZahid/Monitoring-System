from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from app.core.config import settings
from app.shared.enums import UserRole, TokenType


class JWTService:
    def create_access_token(self, user_id: str, username: str, role: UserRole,) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "type": TokenType.ACCESS.value,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

    def decode_token(self, token: str,) -> dict[str, Any]:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )

    def verify_access_token(self, token: str,) -> dict[str, Any]:
        payload = self.decode_token(token)

        if payload.get("type") != TokenType.ACCESS.value:
            raise JWTError("Invalid token type.")

        return payload

jwt_service = JWTService()