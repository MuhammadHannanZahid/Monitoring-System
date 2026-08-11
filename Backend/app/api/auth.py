from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.service import AuthService
from app.shared.authorization import require_admin, require_viewer
from app.shared.constants import Messages
from app.shared.models.auth_user import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
    UserModel,
)
from app.shared.responses import SuccessResponse, success_response

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(request: LoginRequest, service: AuthService = Depends(get_auth_service),):

    tokens = await service.login(
        username=request.username,
        password=request.password,
    )

    return success_response(
        message=Messages.LOGIN_SUCCESS,
        data=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        ),
    )


@router.get("/me", response_model=SuccessResponse[CurrentUserResponse])
async def me(current_user: UserModel = Depends(require_viewer())):
    return success_response(
        message=Messages.CURRENT_USER_RETRIEVED,
        data=CurrentUserResponse(
            id=current_user.id,
            username=current_user.username,
            role=current_user.role,
        ),
    )


@router.post("/logout", response_model=SuccessResponse[None],)
async def logout(current_user: UserModel = Depends(require_viewer()), service: AuthService = Depends(get_auth_service)):
    await service.logout(current_user.id)

    return success_response(
        message=Messages.LOGOUT_SUCCESS,
        data=None,
    )


@router.get("/admin-test", response_model=SuccessResponse[str])
async def admin_test(current_user: UserModel = Depends(require_admin())):
    return success_response(
        message="Admin authorization successful.",
        data="You are an administrator.",
    )
