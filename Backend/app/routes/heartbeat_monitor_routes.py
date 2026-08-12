from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.modules.heartbeat_monitor_manager.dependencies import get_heartbeat_service
from app.modules.heartbeat_monitor_manager.service import HeartbeatMonitorService
from app.service.authorization import require_admin
from app.service.constants import Messages
from app.service.mongo_db.shared_models.models.heartbeat_monitor import CreateHeartbeatMonitorRequest, HeartbeatMonitorResponse, HeartbeatResponse, HeartbeatTokenResponse, RegenerateHeartbeatTokenResponse, UpdateHeartbeatMonitorRequest
from app.service.responses import SuccessResponse, success_response

router = APIRouter(prefix="/heartbeat-monitors", tags=["Heartbeat Monitors"])

@router.post("/create", response_model=SuccessResponse[HeartbeatTokenResponse], dependencies=[Depends(require_admin())])
async def create_monitor(request: CreateHeartbeatMonitorRequest, service: HeartbeatMonitorService = Depends(get_heartbeat_service)):
    monitor = await service.create_monitor(
        name=request.name,
        expected_heartbeat_interval=request.expected_heartbeat_interval,
        grace_period=request.grace_period,
    )

    return success_response(
        message=Messages.monitor_CREATED,
        data=HeartbeatTokenResponse(
            heartbeat_token=monitor.heartbeat_token,
        ),
    )

@router.get("/list_all", response_model=SuccessResponse[list[HeartbeatMonitorResponse]], dependencies=[Depends(require_admin())])
async def list_monitors(service: HeartbeatMonitorService = Depends(get_heartbeat_service)):
    monitors = await service.list_monitors()

    return success_response(
        message=Messages.monitor_FETCHED,
        data=[
            HeartbeatMonitorResponse(
                id=monitor.id,
                name=monitor.name,
                expected_heartbeat_interval=monitor.expected_heartbeat_interval,
                grace_period=monitor.grace_period,
                status=monitor.status.value,
                is_active=monitor.is_active,
                last_heartbeat_at=(
                    monitor.last_heartbeat_at.isoformat()
                    if monitor.last_heartbeat_at
                    else None
                ),
                created_at=monitor.created_at.isoformat(),
                updated_at=monitor.updated_at.isoformat(),
            )
            for monitor in monitors
        ],
    )

@router.get("/{heartbeat_monitor_id}/get_one", response_model=SuccessResponse[HeartbeatMonitorResponse], dependencies=[Depends(require_admin())])
async def get_monitor(heartbeat_monitor_id: str, service: HeartbeatMonitorService = Depends(get_heartbeat_service)):
    monitor = await service.get_monitor(heartbeat_monitor_id)

    if monitor is None:
        raise HTTPException(404)

    return success_response(
        message=Messages.monitor_FETCHED,
        data=HeartbeatMonitorResponse(
            id=monitor.id,
            name=monitor.name,
            expected_heartbeat_interval=monitor.expected_heartbeat_interval,
            grace_period=monitor.grace_period,
            status=monitor.status.value,
            is_active=monitor.is_active,
            last_heartbeat_at=(
                monitor.last_heartbeat_at.isoformat()
                if monitor.last_heartbeat_at
                else None
            ),
            created_at=monitor.created_at.isoformat(),
            updated_at=monitor.updated_at.isoformat(),
        ),
    )

@router.put("/{heartbeat_monitor_id}/update", response_model=SuccessResponse[HeartbeatMonitorResponse], dependencies=[Depends(require_admin())])
async def update_monitor(heartbeat_monitor_id: str, request: UpdateHeartbeatMonitorRequest, service: HeartbeatMonitorService = Depends(get_heartbeat_service)):
    monitor = await service.update_monitor(
        heartbeat_monitor_id,
        name=request.name,
        expected_heartbeat_interval=request.expected_heartbeat_interval,
        grace_period=request.grace_period,
    )

    if monitor is None:
        raise HTTPException(404)

    return success_response(
        message=Messages.monitor_UPDATED,
        data=HeartbeatMonitorResponse(
            id=monitor.id,
            name=monitor.name,
            expected_heartbeat_interval=monitor.expected_heartbeat_interval,
            grace_period=monitor.grace_period,
            status=monitor.status.value,
            is_active=monitor.is_active,
            last_heartbeat_at=(
                monitor.last_heartbeat_at.isoformat()
                if monitor.last_heartbeat_at
                else None
            ),
            created_at=monitor.created_at.isoformat(),
            updated_at=monitor.updated_at.isoformat(),
        ),
    )

@router.delete("/{heartbeat_monitor_id}/delete", response_model=SuccessResponse[None], dependencies=[Depends(require_admin())])
async def delete_monitor(heartbeat_monitor_id: str, service: HeartbeatMonitorService = Depends(get_heartbeat_service)):
    deleted = await service.delete_monitor(heartbeat_monitor_id)

    if not deleted:
        raise HTTPException(404)

    return success_response(
        message=Messages.monitor_DELETED,
        data=None,
    )

@router.post("/heartbeat/{token}", response_model=SuccessResponse[HeartbeatResponse], include_in_schema=False)
async def receive_heartbeat(token: str, service: HeartbeatMonitorService = Depends(get_heartbeat_service)):
    monitor = await service.receive_heartbeat(token)

    if monitor is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid heartbeat token.",
        )

    return success_response(
        message=Messages.heartbeat_RECEIVED,
        data=HeartbeatResponse(
            message=Messages.heartbeat_RECEIVED,
            expected_next_heartbeat_in=monitor.expected_heartbeat_interval,
            server_time=datetime.now(timezone.utc),
            token_rotation_required=False,
        ),
    )

@router.patch("/{heartbeat_monitor_id}/regenerate-token", response_model=SuccessResponse[RegenerateHeartbeatTokenResponse], dependencies=[Depends(require_admin())])
async def regenerate_heartbeat_token(heartbeat_monitor_id: str, service: HeartbeatMonitorService = Depends(get_heartbeat_service)):
    monitor = await service.regenerate_token(heartbeat_monitor_id)

    if monitor is None:
        raise HTTPException(404)

    return success_response(
        message="Heartbeat token regenerated successfully.",
        data=RegenerateHeartbeatTokenResponse(
            heartbeat_token=monitor.heartbeat_token
        )
    )