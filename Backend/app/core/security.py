from secrets import token_urlsafe
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from app.core.logger import get_logger

logger = get_logger(__name__)

class PasswordService:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def hash_password(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify_password(self, password: str, hashed_password: str,) -> bool:
        try:
            return self._hasher.verify(hashed_password, password)
        except (VerifyMismatchError, VerificationError):
            return False

class RefreshTokenService:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def generate_token(self) -> str:
        return token_urlsafe(64)

    def hash_token(self, token: str) -> str:
        return self._hasher.hash(token)

    def verify_token(self, token: str, hashed_token: str,) -> bool:
        try:
            return self._hasher.verify(hashed_token, token)
        except (VerifyMismatchError, VerificationError):
            return False

password_service = PasswordService()
refresh_token_service = RefreshTokenService()