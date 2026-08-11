from fastapi import APIRouter, Depends

from app.modules.ping_monitor.dependencies import get_ping_service
from app.modules.ping_monitor.service import PingMonitorService
from app.shared.authorization import require_admin
from app.shared.constants import Messages
from app.shared.models.ping_monitor import (
    CreatePingMonitorRequest,
    PingMonitorResponse,
    UpdatePingMonitorRequest,
)
from app.shared.responses import SuccessResponse, success_response

router = APIRouter(prefix="/ping-monitors", tags=["Ping Monitors"], dependencies=[Depends(require_admin())])


@router.post("/create", response_model=SuccessResponse[PingMonitorResponse])
async def create_ping_monitor(request: CreatePingMonitorRequest, service: PingMonitorService = Depends(get_ping_service)):
    monitor = await service.create_monitor(
        name=request.name,
        host=request.host,
        check_interval=request.check_interval,
        timeout=request.timeout,
        expected_response_time_ms=request.expected_response_time_ms,
    )

    return success_response(
        message=Messages.monitor_CREATED,
        data=service.to_response(monitor),
    )


@router.get("/list_all", response_model=SuccessResponse[list[PingMonitorResponse]])
async def list_monitors(service: PingMonitorService = Depends(get_ping_service)):
    PING_monitors = await service.list_monitors()

    return success_response(
        message=Messages.monitor_FETCHED,
        data=service.to_response_list(PING_monitors),
    )


@router.get("/{PING_monitor_id}/get_one", response_model=SuccessResponse[PingMonitorResponse])
async def get_ping_monitor(PING_monitor_id: str, service: PingMonitorService = Depends(get_ping_service)):
    monitor = await service.get_monitor(PING_monitor_id)

    return success_response(
        message=Messages.monitor_FETCHED,
        data=service.to_response(monitor),
    )


@router.put("/{PING_monitor_id}/update", response_model=SuccessResponse[PingMonitorResponse])
async def update_ping_monitor(PING_monitor_id: str, request: UpdatePingMonitorRequest, service: PingMonitorService = Depends(get_ping_service)):
    PING_monitor = await service.update_monitor(
        monitor_id=PING_monitor_id,
        name=request.name,
        host=request.host,
        check_interval=request.check_interval,
        expected_response_time_ms=request.expected_response_time_ms,
    )

    return success_response(
        message=Messages.monitor_UPDATED,
        data=service.to_response(PING_monitor),
    )


@router.delete("/{PING_monitor_id}/delete", response_model=SuccessResponse[None])
async def delete_ping_monitor(PING_monitor_id: str, service: PingMonitorService = Depends(get_ping_service)):
    await service.delete_monitor(PING_monitor_id)

    return success_response(
        message=Messages.monitor_DELETED,
        data=None,
    )
