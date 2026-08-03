from fastapi import APIRouter, Depends, HTTPException, status
from app.modules.API_monitor.dependencies import get_API_monitor_service
from app.modules.API_monitor.schemas import CreateApiMonitorRequest, UpdateApiMonitorRequest
from app.modules.API_monitor.service import API_monitorService
from app.shared.mappers.API_monitor_mapper import API_monitorMapper
from app.shared.responses import ApiResponse
from app.modules.API_monitor.schemas import ApiMonitorResponse

router = APIRouter(prefix="/API_monitors", tags=["API Monitors"])

@router.post("/create", response_model=ApiResponse[ApiMonitorResponse], status_code=status.HTTP_201_CREATED)
async def create_monitor(request: CreateApiMonitorRequest, service: API_monitorService = Depends(get_API_monitor_service)):
    try:
        monitor = await service.create_monitor(request)

        return ApiResponse(
            success=True,
            message="API monitor created successfully.",
            data=API_monitorMapper.to_response(monitor),
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
        data=API_monitorMapper.to_response_list(monitors),
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
        data=API_monitorMapper.to_response(monitor),
    )

@router.put("/{monitor_id}", response_model=ApiResponse[ApiMonitorResponse])
async def update_monitor(monitor_id: str, request: UpdateApiMonitorRequest, service: API_monitorService = Depends(get_API_monitor_service)):
    try:
        monitor = await service.update_monitor(monitor_id, request)

        if monitor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API monitor not found.",
            )

        return ApiResponse(
            success=True,
            message="API monitor updated successfully.",
            data=API_monitorMapper.to_response(monitor),
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

@router.patch("/{monitor_id}/activate", response_model=ApiResponse[ApiMonitorResponse])
async def activate_monitor(monitor_id: str, service: API_monitorService = Depends(get_API_monitor_service)):
    success = await service.activate_monitor(monitor_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API monitor not found.",
        )

    monitor = await service.get_monitor(monitor_id)
    return ApiResponse(
        success=True,
        message="API monitor activated successfully.",
    )

@router.patch("/{monitor_id}/deactivate", response_model=ApiResponse[ApiMonitorResponse])
async def deactivate_monitor(monitor_id: str, service: API_monitorService = Depends(get_API_monitor_service)):
    success = await service.deactivate_monitor(monitor_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API monitor not found.",
        )
    monitor = await service.get_monitor(monitor_id)
    return ApiResponse(
        success=True,
        message="API monitor deactivated successfully.",
    )