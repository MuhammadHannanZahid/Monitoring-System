import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from dotenv import load_dotenv
from jose import JWTError, jwt
from app.shared.models.auth_user import TokenType, UserRole

class JWTService:
    def create_access_token(self, user_id: str, username: str, role: UserRole,) -> str:
        load_dotenv()
        expire = datetime.now(timezone.utc) + timedelta(minutes=int(os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"]))
        payload = {
            "sub": user_id,
            "username": username,
            "role": role.value,
            "type": TokenType.ACCESS.value,
            "exp": expire,
        }
        return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=os.environ["JWT_ALGORITHM"])

    def create_refresh_token(self, user_id: str, username: str, role: UserRole) -> tuple[str, datetime]:
        load_dotenv()
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(days=int(os.environ["REFRESH_TOKEN_EXPIRE_DAYS"]))
        payload = {
            "sub": user_id,
            "username": username,
            "role": role.value,
            "type": TokenType.REFRESH.value,
            "iat": issued_at,
            "exp": expires_at,
            "jti": uuid.uuid4().hex,
        }
        token = jwt.encode(
            payload,
            os.environ["JWT_SECRET"],
            algorithm=os.environ["JWT_ALGORITHM"],
        )
        return token, expires_at

    def decode_token(self, token: str,) -> dict[str, Any]:
        load_dotenv()
        return jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[os.environ["JWT_ALGORITHM"]])

    def verify_access_token(self, token: str,) -> dict[str, Any]:
        payload = self.decode_token(token)
        if payload.get("type") != TokenType.ACCESS.value:
            raise JWTError("Invalid token type.")
        return payload

    def verify_refresh_token(self, token: str) -> dict[str, Any]:
        payload = self.decode_token(token)
        if payload.get("type") != TokenType.REFRESH.value:
            raise JWTError("Invalid token type.")
        return payload

jwt_service = JWTService()