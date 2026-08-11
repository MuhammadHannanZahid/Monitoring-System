from fastapi import APIRouter, Depends

from app.modules.HTTP_monitor.dependencies import get_HTTP_monitor_service
from app.modules.HTTP_monitor.service import HTTP_monitorService
from app.shared.authorization import require_admin
from app.shared.constants import Messages
from app.shared.models.HTTP_monitor import (
    CreateHTTP_monitorRequest,
    HTTP_monitorResponse,
    UpdateHTTP_monitorRequest,
)
from app.shared.responses import SuccessResponse, success_response

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
        data=service.to_response(HTTP_monitor),
    )


@router.get("/list_all", response_model=SuccessResponse[list[HTTP_monitorResponse]])
async def list_monitors(service: HTTP_monitorService = Depends(get_HTTP_monitor_service)):
    HTTP_monitors = await service.list_monitors()

    return success_response(
        message=Messages.monitor_FETCHED,
        data=service.to_response_list(HTTP_monitors),
    )


@router.get("/{HTTP_monitor_id}/get_one", response_model=SuccessResponse[HTTP_monitorResponse])
async def get_HTTP_monitor(HTTP_monitor_id: str, service: HTTP_monitorService = Depends(get_HTTP_monitor_service)):
    HTTP_monitor = await service.get_monitor(HTTP_monitor_id)

    return success_response(
        message=Messages.monitor_FETCHED,
        data=service.to_response(HTTP_monitor),
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
        data=service.to_response(HTTP_monitor),
    )


@router.delete("/{HTTP_monitor_id}/delete", response_model=SuccessResponse[None])
async def delete_HTTP_monitor(HTTP_monitor_id: str, service: HTTP_monitorService = Depends(get_HTTP_monitor_service)):
    await service.delete_monitor(HTTP_monitor_id)

    return success_response(
        message=Messages.monitor_DELETED,
        data=None,
    )
