from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth_profiles.dependencies import get_auth_profile_service
from app.modules.auth_profiles.service import AuthProfileService
from app.shared.authorization import require_admin
from app.shared.models.auth_profile import (
    AuthProfileResponse,
    CreateAuthProfileRequest,
    UpdateAuthProfileRequest,
)
from app.shared.responses import ApiResponse

router = APIRouter(
    prefix="/auth-profiles",
    tags=["Auth Profiles"],
    dependencies=[Depends(require_admin())],
)


@router.post(
    "/create",
    response_model=ApiResponse[AuthProfileResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    request: CreateAuthProfileRequest,
    service: AuthProfileService = Depends(get_auth_profile_service),
):
    try:
        profile = await service.create_profile(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(
        success=True,
        message="Auth profile created successfully.",
        data=AuthProfileResponse(
            id=profile.id,
            name=profile.name,
            login_url=profile.login_url,
            method=profile.method,
            credential_fields=sorted(profile.credentials),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ),
    )


@router.get("/list_all", response_model=ApiResponse[list[AuthProfileResponse]])
async def list_profiles(
    service: AuthProfileService = Depends(get_auth_profile_service),
):
    profiles = await service.list_profiles()
    return ApiResponse(
        success=True,
        message="Auth profiles retrieved successfully.",
        data=[
            AuthProfileResponse(
                id=profile.id,
                name=profile.name,
                login_url=profile.login_url,
                method=profile.method,
                credential_fields=sorted(profile.credentials),
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
            for profile in profiles
        ],
    )


@router.get("/{profile_id}", response_model=ApiResponse[AuthProfileResponse])
async def get_profile(
    profile_id: str,
    service: AuthProfileService = Depends(get_auth_profile_service),
):
    profile = await service.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Auth profile not found.")
    return ApiResponse(
        success=True,
        message="Auth profile retrieved successfully.",
        data=AuthProfileResponse(
            id=profile.id,
            name=profile.name,
            login_url=profile.login_url,
            method=profile.method,
            credential_fields=sorted(profile.credentials),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ),
    )


@router.put("/{profile_id}", response_model=ApiResponse[AuthProfileResponse])
async def update_profile(
    profile_id: str,
    request: UpdateAuthProfileRequest,
    service: AuthProfileService = Depends(get_auth_profile_service),
):
    try:
        profile = await service.update_profile(profile_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if profile is None:
        raise HTTPException(status_code=404, detail="Auth profile not found.")
    return ApiResponse(
        success=True,
        message="Auth profile updated successfully.",
        data=AuthProfileResponse(
            id=profile.id,
            name=profile.name,
            login_url=profile.login_url,
            method=profile.method,
            credential_fields=sorted(profile.credentials),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ),
    )


@router.delete("/{profile_id}", response_model=ApiResponse[None])
async def delete_profile(
    profile_id: str,
    service: AuthProfileService = Depends(get_auth_profile_service),
):
    if not await service.delete_profile(profile_id):
        raise HTTPException(status_code=404, detail="Auth profile not found.")
    return ApiResponse(
        success=True,
        message="Auth profile deleted successfully.",
    )
