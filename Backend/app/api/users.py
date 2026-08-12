from fastapi import APIRouter, Depends
from app.modules.users.dependencies import get_user_service
from app.modules.users.service import UserService
from app.shared.authorization import require_admin
from app.shared.constants import Messages
from app.shared.models.auth_user import CreateUserRequest, UpdateUserRequest, UserResponse
from app.shared.responses import SuccessResponse, success_response

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(require_admin())])

@router.post("/create",response_model=SuccessResponse[UserResponse])
async def create_user(request: CreateUserRequest, service: UserService = Depends(get_user_service)):
    user = await service.create_user(
        username=request.username,
        password=request.password,
        role=request.role,
    )

    return success_response(
        message=Messages.USER_CREATED,
        data=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
        ),
    )

@router.get("/list", response_model=SuccessResponse[list[UserResponse]])
async def list_users(service: UserService = Depends(get_user_service)):
    users = await service.list_users()

    return success_response(
        message=Messages.USERS_FETCHED,
        data=[
            UserResponse(
                id=user.id,
                username=user.username,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login=user.last_login,
            )
            for user in users
        ],
    )

@router.get("/{user_id}/get_one", response_model=SuccessResponse[UserResponse])
async def get_user(user_id: str, service: UserService = Depends(get_user_service)):
    user = await service.get_user(user_id)

    return success_response(
        message=Messages.USER_FETCHED,
        data=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
        ),
    )

@router.put("/{user_id}/update", response_model=SuccessResponse[UserResponse])
async def update_user(user_id: str, request: UpdateUserRequest, service: UserService = Depends(get_user_service)):
    user = await service.update_user(
        user_id=user_id,
        username=request.username,
        password=request.password,
        role=request.role,
        is_active=request.is_active,
    )

    return success_response(
        message=Messages.USER_UPDATED,
        data=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
        ),
    )

@router.delete("/{user_id}/delete", response_model=SuccessResponse[None])
async def delete_user(user_id: str, service: UserService = Depends(get_user_service)):
    await service.delete_user(user_id)

    return success_response(
        message=Messages.USER_DELETED,
        data=None,
    )