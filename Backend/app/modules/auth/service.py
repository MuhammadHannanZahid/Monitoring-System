from app.core.jwt import JWTService
from app.core.security import PasswordService, RefreshTokenService
from app.modules.auth.dto import AuthTokens
from app.shared.models.user import UserModel
from app.modules.auth.repository import AuthRepository
from app.shared.exceptions import AuthenticationError, NotFoundError
from app.shared.constants import Messages


class AuthService:
    def __init__(self, repository: AuthRepository, password_service: PasswordService, jwt_service: JWTService, refresh_token_service: RefreshTokenService,) -> None:
        self.repository = repository
        self.password_service = password_service
        self.jwt_service = jwt_service
        self.refresh_token_service = refresh_token_service

    async def login(self, username: str, password: str,) -> AuthTokens:
        user = await self.repository.get_by_username(username)

        if user is None or user.id is None:
            raise AuthenticationError(Messages.INVALID_CREDENTIALS)

        valid_password = self.password_service.verify_password(
            password=password,
            hashed_password=user.password_hash,
        )

        if not valid_password:
            raise AuthenticationError(Messages.INVALID_CREDENTIALS)

        refresh_token = self.refresh_token_service.generate_token()
        refresh_token_hash = (self.refresh_token_service.hash_token(refresh_token))

        updated_refresh = await self.repository.update_refresh_token(user.id, refresh_token_hash)
        if not updated_refresh:
            raise NotFoundError("User not found.")

        updated_last = await self.repository.update_last_login(user.id)
        if not updated_last:
            raise NotFoundError("User not found.")

        access_token = self.jwt_service.create_access_token(user_id=user.id, username=user.username, role=user.role,)

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def get_current_user(self, user_id: str,) -> UserModel:
        user = await self.repository.get_by_id(user_id)

        if user is None:
            raise NotFoundError("User not found.")

        return user

    async def logout(self, user_id: str,) -> None:
        updated = await self.repository.clear_refresh_token(user_id)

        if not updated:
            raise NotFoundError(Messages.USER_NOT_FOUND)