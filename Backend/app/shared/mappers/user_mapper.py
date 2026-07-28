from app.shared.models.user import UserModel
from app.modules.users.schemas import UserResponse

class UserMapper:
    @staticmethod
    def to_response(user: UserModel) -> UserResponse:
        return UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
        )

    @staticmethod
    def to_response_list(users: list[UserModel]) -> list[UserResponse]:
        return [UserMapper.to_response(user) for user in users]