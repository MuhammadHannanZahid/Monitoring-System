from fastapi import APIRouter, Depends, HTTPException, status
from odmantic import AIOEngine
from app.modules.api_monitor_manager.service import API_monitorService
from app.modules.orion_login_manager.service import AuthProfileService
from app.service.authorization import require_admin
from app.service.mongo_db.mongo_controller import get_engine
from app.service.mongo_db.shared_models.db_api_monitor_model import ApiMonitorResponse, CreateApiMonitorRequest, UpdateApiMonitorRequest
from app.service.responses import ApiResponse


def get_API_monitor_service(
    engine: AIOEngine = Depends(get_engine),
) -> API_monitorService:
    return API_monitorService(engine, AuthProfileService(engine))

router = APIRouter(prefix="/API_monitors", tags=["API Monitors"], dependencies=[Depends(require_admin())])

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
            data=ApiMonitorResponse(
                id=monitor.id,
                name=monitor.name,
                url=monitor.url,
                method=monitor.method,
                headers=monitor.headers,
                request_body=monitor.request_body,
                expected_status_code=monitor.expected_status_code,
                expected_json=monitor.expected_json,
                check_interval=monitor.check_interval,
                timeout=monitor.timeout,
                is_active=monitor.is_active,
                created_by=monitor.created_by,
                created_at=monitor.created_at,
                updated_at=monitor.updated_at,
                last_checked_at=monitor.last_checked_at,
                last_status_code=monitor.last_status_code,
                last_response_time_ms=monitor.last_response_time_ms,
                status=monitor.status,
                expected_response_time_ms=monitor.expected_response_time_ms,
                expected_headers=monitor.expected_headers,
                expected_content_type=monitor.expected_content_type,
            ),
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
        data=[
            ApiMonitorResponse(
                id=monitor.id,
                name=monitor.name,
                url=monitor.url,
                method=monitor.method,
                headers=monitor.headers,
                request_body=monitor.request_body,
                expected_status_code=monitor.expected_status_code,
                expected_json=monitor.expected_json,
                check_interval=monitor.check_interval,
                timeout=monitor.timeout,
                is_active=monitor.is_active,
                created_by=monitor.created_by,
                created_at=monitor.created_at,
                updated_at=monitor.updated_at,
                last_checked_at=monitor.last_checked_at,
                last_status_code=monitor.last_status_code,
                last_response_time_ms=monitor.last_response_time_ms,
                status=monitor.status,
                expected_response_time_ms=monitor.expected_response_time_ms,
                expected_headers=monitor.expected_headers,
                expected_content_type=monitor.expected_content_type,
            )
            for monitor in monitors
        ],
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
        data=ApiMonitorResponse(
            id=monitor.id,
            name=monitor.name,
            url=monitor.url,
            method=monitor.method,
            headers=monitor.headers,
            request_body=monitor.request_body,
            expected_status_code=monitor.expected_status_code,
            expected_json=monitor.expected_json,
            check_interval=monitor.check_interval,
            timeout=monitor.timeout,
            is_active=monitor.is_active,
            created_by=monitor.created_by,
            created_at=monitor.created_at,
            updated_at=monitor.updated_at,
            last_checked_at=monitor.last_checked_at,
            last_status_code=monitor.last_status_code,
            last_response_time_ms=monitor.last_response_time_ms,
            status=monitor.status,
            expected_response_time_ms=monitor.expected_response_time_ms,
            expected_headers=monitor.expected_headers,
            expected_content_type=monitor.expected_content_type,
        ),
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
            data=ApiMonitorResponse(
                id=monitor.id,
                name=monitor.name,
                url=monitor.url,
                method=monitor.method,
                headers=monitor.headers,
                request_body=monitor.request_body,
                expected_status_code=monitor.expected_status_code,
                expected_json=monitor.expected_json,
                check_interval=monitor.check_interval,
                timeout=monitor.timeout,
                is_active=monitor.is_active,
                created_by=monitor.created_by,
                created_at=monitor.created_at,
                updated_at=monitor.updated_at,
                last_checked_at=monitor.last_checked_at,
                last_status_code=monitor.last_status_code,
                last_response_time_ms=monitor.last_response_time_ms,
                status=monitor.status,
                expected_response_time_ms=monitor.expected_response_time_ms,
                expected_headers=monitor.expected_headers,
                expected_content_type=monitor.expected_content_type,
            ),
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
