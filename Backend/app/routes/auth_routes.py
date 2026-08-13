from fastapi import APIRouter, Depends, Response
from app.modules.auth_manager.auth_manager import AuthManager
from app.service.authorization import (
    clear_auth_cookies,
    get_auth_service,
    require_admin,
    require_viewer,
    set_auth_cookies,
)
from app.service.constants import Messages
from app.service.mongo_db.shared_models.db_user_account_model import CurrentUserResponse, LoginRequest, TokenResponse
from app.service.responses import SuccessResponse, success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(request: LoginRequest, response: Response, service: AuthManager = Depends(get_auth_service)):
    data = await service.login(
        username=request.username,
        password=request.password,
    )
    set_auth_cookies(response, data)

    return success_response(
        message=Messages.LOGIN_SUCCESS,
        data=data,
    )

@router.get("/me", response_model=SuccessResponse[CurrentUserResponse])
async def me(current_user: CurrentUserResponse = Depends(require_viewer())):
    return success_response(
        message=Messages.CURRENT_USER_RETRIEVED,
        data=current_user,
    )

@router.post("/logout", response_model=SuccessResponse[None],)
async def logout(response: Response, current_user: CurrentUserResponse = Depends(require_viewer()), service: AuthManager = Depends(get_auth_service)):
    await service.logout(current_user.id)
    clear_auth_cookies(response)

    return success_response(
        message=Messages.LOGOUT_SUCCESS,
        data=None,
    )

@router.get("/admin-test", response_model=SuccessResponse[str])
async def admin_test(current_user: CurrentUserResponse = Depends(require_admin())):
    return success_response(
        message="Admin authorization successful.",
        data="You are an administrator.",
    )
