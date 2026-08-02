from fastapi import APIRouter, Depends, Query
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.schemas import DashboardSummaryResponse, DashboardIncidentResponse, DashboardActivityResponse, StatusHistoryResponse, UptimeResponse, ResponseHistoryResponse
from app.modules.dashboard.service import DashboardService
from app.shared.authorization import require_viewer
from app.shared.constants import Messages
from app.shared.responses import SuccessResponse, success_response

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_viewer())],
)

@router.get("/summary", response_model=SuccessResponse[DashboardSummaryResponse])
async def get_summary(service: DashboardService = Depends(get_dashboard_service)):
    summary = await service.get_summary()

    return success_response(
        message=Messages.DASHBOARD_FETCHED,
        data=summary
    )

@router.get("/incidents", response_model=SuccessResponse[list[DashboardIncidentResponse]])
async def get_dashboard_incidents(service: DashboardService = Depends(get_dashboard_service)):
    return success_response(
        message=Messages.DASHBOARD_FETCHED,
        data=await service.get_recent_incidents(),
    )

@router.get("/activity", response_model=SuccessResponse[list[DashboardActivityResponse]])
async def get_dashboard_activity(service: DashboardService = Depends(get_dashboard_service)):
    return success_response(
        message=Messages.DASHBOARD_FETCHED,
        data=await service.get_recent_activity(),
    )

@router.get("/response-history/{monitor_id}", response_model=SuccessResponse[ResponseHistoryResponse])
async def get_response_history(monitor_id: str, days: int = Query(7, ge=1, le=365), service: DashboardService = Depends(get_dashboard_service)):
    return success_response(
        message=Messages.DASHBOARD_FETCHED,
        data=await service.get_response_history(monitor_id, days)
    )

@router.get("/uptime/{monitor_id}", response_model=SuccessResponse[UptimeResponse])
async def get_uptime(monitor_id: str, days: int = Query(7, ge=1, le=365), service: DashboardService = Depends(get_dashboard_service)):
    return success_response(
        message=Messages.DASHBOARD_FETCHED,
        data=await service.get_uptime(monitor_id, days)
    )

@router.get("/status-history/{monitor_id}", response_model=SuccessResponse[StatusHistoryResponse])
async def get_status_history(monitor_id: str, days: int = Query(7, ge=1, le=365), service: DashboardService = Depends(get_dashboard_service)):
    return success_response(
        message=Messages.DASHBOARD_FETCHED,
        data=await service.get_status_history(monitor_id, days)
    )

