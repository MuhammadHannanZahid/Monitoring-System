from datetime import datetime, timezone
from app.core.security import PasswordService
from app.modules.users.repository import UserRepository
from app.shared.constants import Messages
from app.shared.enums import UserRole
from app.shared.exceptions import ConflictError, NotFoundError, AuthorizationError
from app.shared.models.auth_user import UserModel

class UserService:
    def __init__(self, repository: UserRepository, password_service: PasswordService):
        self.repository = repository
        self.password_service = password_service

    def _hash_password(self, password: str) -> str:
        return self.password_service.hash_password(password)
    
    async def create_user(self, username: str, password: str, role: UserRole) -> UserModel:
        username_exists = await self.repository.username_exists(username)

        if username_exists:
            raise ConflictError(Messages.USERNAME_ALREADY_EXISTS)

        if role == UserRole.ADMIN:
            raise AuthorizationError(Messages.ADMIN_CREATION_NOT_ALLOWED)

        now = datetime.now(timezone.utc)

        user = UserModel(
            username=username,
            password_hash=self.password_service.hash_password(password),
            role=role,
            is_active=True,
            refresh_token_hash=None,
            created_at=now,
            updated_at=now,
            last_login=None,
        )

        user_id = await self.repository.create_user(user)
        created_user = await self.repository.get_by_id(user_id)

        if created_user is None:
            raise RuntimeError("Failed to retrieve newly created user.")

        return created_user

    async def get_user(self, user_id: str) -> UserModel:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(Messages.USER_NOT_FOUND)
        return user

    async def list_users(self) -> list[UserModel]:
        return await self.repository.list_users()

    async def update_user(self, user_id: str, username: str | None = None, password: str | None = None, role: UserRole | None = None, is_active: bool | None = None) -> UserModel:
        user = await self.get_user(user_id)
        update_data: dict[str, object] = {}

        if username is not None:
            if username != user.username:
                exists = await self.repository.username_exists(username)

                if exists:
                    raise ConflictError(Messages.USERNAME_ALREADY_EXISTS)

                if role == UserRole.ADMIN:
                    raise AuthorizationError(Messages.ADMIN_PROMOTION_NOT_ALLOWED)
                update_data["username"] = username

        if password is not None:
            update_data["password_hash"] = self._hash_password(password)

        if role is not None:
            existing_user = await self.repository.get_by_id(user_id)
            if existing_user is None:
                raise NotFoundError(Messages.USER_NOT_FOUND)

            if existing_user.role == UserRole.ADMIN and role != UserRole.ADMIN:
                raise AuthorizationError(Messages.ADMIN_ROLE_CHANGE_NOT_ALLOWED)

            update_data["role"] = role

        if is_active is not None:
            update_data["is_active"] = is_active

        if update_data:
            await self.repository.update_user(user_id, update_data)

        updated_user = await self.get_user(user_id)
        return updated_user

    async def delete_user(self, user_id: str) -> None:
        user = await self.repository.get_by_id(user_id)
        if user.role == UserRole.ADMIN:
            raise AuthorizationError(Messages.ADMIN_DELETION_NOT_ALLOWED)
        await self.get_user(user_id)
        await self.repository.delete_user(user_id)

    async def activate_user(self, user_id: str) -> UserModel:
        await self.get_user(user_id)
        await self.repository.set_active(user_id,True)
        return await self.get_user(user_id)

    async def deactivate_user(self, user_id: str) -> UserModel:
        user = await self.repository.get_by_id(user_id)
        if user.role == UserRole.ADMIN:
            raise AuthorizationError(Messages.ADMIN_DEACTIVATION_NOT_ALLOWED)

        await self.get_user(user_id)
        await self.repository.set_active(user_id,False)
        return await self.get_user(user_id)