from fastapi import APIRouter, Depends, HTTPException
from app.modules.http_monitor_manager.dependencies import get_HTTP_monitor_service
from app.modules.http_monitor_manager.service import HTTP_monitorService
from app.service.authorization import require_admin
from app.service.constants import Messages
from app.service.mongo_db.shared_models.models.HTTP_monitor import CreateHTTP_monitorRequest, HTTP_monitorResponse, UpdateHTTP_monitorRequest
from app.service.responses import SuccessResponse, success_response

router = APIRouter(prefix="/HTTP_monitors", tags=["HTTP_monitors"], dependencies=[Depends(require_admin())])

@router.post("/create", response_model=SuccessResponse[HTTP_monitorResponse])
async def create_HTTP_monitor(request: CreateHTTP_monitorRequest, service: HTTP_monitorService = Depends(get_HTTP_monitor_service)):
    HTTP_monitor = await service.create_monitor(
        name=request.name,
        url=request.url,
        check_interval=request.check_interval,
        timeout=request.timeout,
        expected_status_code=request.expected_status_code,
        expected_response_time_ms=request.expected_response_time_ms,
    )

    return success_response(
        message=Messages.monitor_CREATED,
        data=HTTP_monitorResponse(
            id=HTTP_monitor.id,
            name=HTTP_monitor.name,
            url=HTTP_monitor.url,
            check_interval=HTTP_monitor.check_interval,
            timeout=HTTP_monitor.timeout,
            expected_status_code=HTTP_monitor.expected_status_code,
            is_active=HTTP_monitor.is_active,
            created_at=HTTP_monitor.created_at,
            updated_at=HTTP_monitor.updated_at,
            last_checked_at=HTTP_monitor.last_checked_at,
            last_status_code=HTTP_monitor.last_status_code,
            last_response_time_ms=HTTP_monitor.last_response_time_ms,
            status=HTTP_monitor.status,
            expected_response_time_ms=HTTP_monitor.expected_response_time_ms,
        ),
    )

@router.get("/list_all", response_model=SuccessResponse[list[HTTP_monitorResponse]])
async def list_monitors(service: HTTP_monitorService = Depends(get_HTTP_monitor_service)):
    HTTP_monitors = await service.list_monitors()

    return success_response(
        message=Messages.monitor_FETCHED,
        data=[
            HTTP_monitorResponse(
                id=HTTP_monitor.id,
                name=HTTP_monitor.name,
                url=HTTP_monitor.url,
                check_interval=HTTP_monitor.check_interval,
                timeout=HTTP_monitor.timeout,
                expected_status_code=HTTP_monitor.expected_status_code,
                is_active=HTTP_monitor.is_active,
                created_at=HTTP_monitor.created_at,
                updated_at=HTTP_monitor.updated_at,
                last_checked_at=HTTP_monitor.last_checked_at,
                last_status_code=HTTP_monitor.last_status_code,
                last_response_time_ms=HTTP_monitor.last_response_time_ms,
                status=HTTP_monitor.status,
                expected_response_time_ms=HTTP_monitor.expected_response_time_ms,
            )
            for HTTP_monitor in HTTP_monitors
        ],
    )

@router.get("/{HTTP_monitor_id}/get_one", response_model=SuccessResponse[HTTP_monitorResponse])
async def get_HTTP_monitor(HTTP_monitor_id: str, service: HTTP_monitorService = Depends(get_HTTP_monitor_service)):
    HTTP_monitor = await service.get_monitor(HTTP_monitor_id)
    if HTTP_monitor is None:
        raise HTTPException(status_code=404, detail=Messages.monitor_NOT_FOUND)

    return success_response(
        message=Messages.monitor_FETCHED,
        data=HTTP_monitorResponse(
            id=HTTP_monitor.id,
            name=HTTP_monitor.name,
            url=HTTP_monitor.url,
            check_interval=HTTP_monitor.check_interval,
            timeout=HTTP_monitor.timeout,
            expected_status_code=HTTP_monitor.expected_status_code,
            is_active=HTTP_monitor.is_active,
            created_at=HTTP_monitor.created_at,
            updated_at=HTTP_monitor.updated_at,
            last_checked_at=HTTP_monitor.last_checked_at,
            last_status_code=HTTP_monitor.last_status_code,
            last_response_time_ms=HTTP_monitor.last_response_time_ms,
            status=HTTP_monitor.status,
            expected_response_time_ms=HTTP_monitor.expected_response_time_ms,
        ),
    )

@router.put("/{HTTP_monitor_id}/update", response_model=SuccessResponse[HTTP_monitorResponse])
async def update_HTTP_monitor(HTTP_monitor_id: str, request: UpdateHTTP_monitorRequest, service: HTTP_monitorService = Depends(get_HTTP_monitor_service)):
    HTTP_monitor = await service.update_monitor(
        HTTP_monitor_id=HTTP_monitor_id,
        name=request.name,
        url=request.url,
        check_interval=request.check_interval,
        timeout=request.timeout,
        expected_status_code=request.expected_status_code,
        expected_response_time_ms=request.expected_response_time_ms,
    )

    return success_response(
        message=Messages.monitor_UPDATED,
        data=HTTP_monitorResponse(
            id=HTTP_monitor.id,
            name=HTTP_monitor.name,
            url=HTTP_monitor.url,
            check_interval=HTTP_monitor.check_interval,
            timeout=HTTP_monitor.timeout,
            expected_status_code=HTTP_monitor.expected_status_code,
            is_active=HTTP_monitor.is_active,
            created_at=HTTP_monitor.created_at,
            updated_at=HTTP_monitor.updated_at,
            last_checked_at=HTTP_monitor.last_checked_at,
            last_status_code=HTTP_monitor.last_status_code,
            last_response_time_ms=HTTP_monitor.last_response_time_ms,
            status=HTTP_monitor.status,
            expected_response_time_ms=HTTP_monitor.expected_response_time_ms,
        ),
    )

@router.delete("/{HTTP_monitor_id}/delete", response_model=SuccessResponse[None])
async def delete_HTTP_monitor(HTTP_monitor_id: str, service: HTTP_monitorService = Depends(get_HTTP_monitor_service)):
    await service.delete_monitor(HTTP_monitor_id)

    return success_response(
        message=Messages.monitor_DELETED,
        data=None,
    )