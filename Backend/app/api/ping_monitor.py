from fastapi import APIRouter, Depends
from app.modules.ping_monitor.dependencies import get_ping_service
from app.modules.ping_monitor.service import PingMonitorService
from app.shared.authorization import require_admin
from app.shared.constants import Messages
from app.shared.models.ping_monitor import CreatePingMonitorRequest, PingMonitorResponse, UpdatePingMonitorRequest
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
        data=PingMonitorResponse(
            id=monitor.id,
            name=monitor.name,
            host=monitor.host,
            check_interval=monitor.check_interval,
            timeout=monitor.timeout,
            expected_response_time_ms=monitor.expected_response_time_ms,
            is_active=monitor.is_active,
            created_by=monitor.created_by,
            created_at=monitor.created_at,
            updated_at=monitor.updated_at,
            last_checked_at=monitor.last_checked_at,
            last_status_code=monitor.last_status_code,
            last_response_time_ms=monitor.last_response_time_ms,
            status=monitor.status,
        ),
    )

@router.get("/list_all", response_model=SuccessResponse[list[PingMonitorResponse]])
async def list_monitors(service: PingMonitorService = Depends(get_ping_service)):
    PING_monitors = await service.list_monitors()

    return success_response(
        message=Messages.monitor_FETCHED,
        data=[
            PingMonitorResponse(
                id=monitor.id,
                name=monitor.name,
                host=monitor.host,
                check_interval=monitor.check_interval,
                timeout=monitor.timeout,
                expected_response_time_ms=monitor.expected_response_time_ms,
                is_active=monitor.is_active,
                created_by=monitor.created_by,
                created_at=monitor.created_at,
                updated_at=monitor.updated_at,
                last_checked_at=monitor.last_checked_at,
                last_status_code=monitor.last_status_code,
                last_response_time_ms=monitor.last_response_time_ms,
                status=monitor.status,
            )
            for monitor in PING_monitors
        ],
    )

@router.get("/{PING_monitor_id}/get_one", response_model=SuccessResponse[PingMonitorResponse])
async def get_ping_monitor(PING_monitor_id: str, service: PingMonitorService = Depends(get_ping_service)):
    monitor = await service.get_monitor(PING_monitor_id)

    return success_response(
        message=Messages.monitor_FETCHED,
        data=PingMonitorResponse(
            id=monitor.id,
            name=monitor.name,
            host=monitor.host,
            check_interval=monitor.check_interval,
            timeout=monitor.timeout,
            expected_response_time_ms=monitor.expected_response_time_ms,
            is_active=monitor.is_active,
            created_by=monitor.created_by,
            created_at=monitor.created_at,
            updated_at=monitor.updated_at,
            last_checked_at=monitor.last_checked_at,
            last_status_code=monitor.last_status_code,
            last_response_time_ms=monitor.last_response_time_ms,
            status=monitor.status,
        ),
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
        data=PingMonitorResponse(
            id=PING_monitor.id,
            name=PING_monitor.name,
            host=PING_monitor.host,
            check_interval=PING_monitor.check_interval,
            timeout=PING_monitor.timeout,
            expected_response_time_ms=PING_monitor.expected_response_time_ms,
            is_active=PING_monitor.is_active,
            created_by=PING_monitor.created_by,
            created_at=PING_monitor.created_at,
            updated_at=PING_monitor.updated_at,
            last_checked_at=PING_monitor.last_checked_at,
            last_status_code=PING_monitor.last_status_code,
            last_response_time_ms=PING_monitor.last_response_time_ms,
            status=PING_monitor.status,
        ),
    )

@router.delete("/{PING_monitor_id}/delete", response_model=SuccessResponse[None])
async def delete_ping_monitor(PING_monitor_id: str, service: PingMonitorService = Depends(get_ping_service)):
    await service.delete_monitor(PING_monitor_id)

    return success_response(
        message=Messages.monitor_DELETED,
        data=None,
    )