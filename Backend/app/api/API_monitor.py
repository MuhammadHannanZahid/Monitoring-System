from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.API_monitor.dependencies import get_API_monitor_service
from app.modules.API_monitor.service import API_monitorService
from app.shared.authorization import require_admin
from app.shared.models.api_monitor import (
    ApiMonitorResponse,
    CreateApiMonitorRequest,
    UpdateApiMonitorRequest,
)
from app.shared.responses import ApiResponse

router = APIRouter(
    prefix="/API_monitors",
    tags=["API Monitors"],
    dependencies=[Depends(require_admin())],
)


@router.post("/create", response_model=ApiResponse[ApiMonitorResponse], status_code=status.HTTP_201_CREATED)
async def create_monitor(request: CreateApiMonitorRequest, service: API_monitorService = Depends(get_API_monitor_service)):
    try:
        monitor = await service.create_monitor(
            request=request,
            expected_response_time_ms=request.expected_response_time_ms,
        )

        return ApiResponse(
            success=True,
            message="API monitor created successfully.",
            data=service.to_response(monitor),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/list_all", response_model=ApiResponse[list[ApiMonitorResponse]])
async def list_monitors(service: API_monitorService = Depends(get_API_monitor_service)):
    monitors = await service.list_monitors()

    return ApiResponse(
        success=True,
        message="API monitors retrieved successfully.",
        data=service.to_response_list(monitors),
    )


@router.get("/{monitor_id}", response_model=ApiResponse[ApiMonitorResponse])
async def get_monitor(monitor_id: str, service: API_monitorService = Depends(get_API_monitor_service)):
    monitor = await service.get_monitor(monitor_id)

    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API monitor not found.",
        )

    return ApiResponse(
        success=True,
        message="API monitor retrieved successfully.",
        data=service.to_response(monitor),
    )


@router.put("/{monitor_id}", response_model=ApiResponse[ApiMonitorResponse])
async def update_monitor(monitor_id: str, request: UpdateApiMonitorRequest, service: API_monitorService = Depends(get_API_monitor_service)):
    try:
        monitor = await service.update_monitor(
            monitor_id,
            request,
            request.expected_response_time_ms,
        )

        if monitor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API monitor not found.",
            )

        return ApiResponse(
            success=True,
            message="API monitor updated successfully.",
            data=service.to_response(monitor),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete("/{monitor_id}", response_model=ApiResponse[None])
async def delete_monitor(monitor_id: str, service: API_monitorService = Depends(get_API_monitor_service)):
    deleted = await service.delete_monitor(monitor_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API monitor not found.",
        )

    return ApiResponse(
        success=True,
        message="Deleted successfully."
    )
