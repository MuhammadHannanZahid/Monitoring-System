from fastapi import APIRouter, Depends, Query
import app.modules.monitoring_controller.scheduler as scheduler_state
from app.modules.insight_manager.service import DashboardService
from app.modules.monitoring_controller.service import MonitorService
from app.service.authorization import require_viewer
from app.service.constants import Messages
from app.service.mongo_db.shared_models.db_insight_model import DashboardActivityResponse, DashboardIncidentResponse, DashboardSummaryResponse, ResponseHistoryResponse, StatusHistoryResponse, UptimeResponse
from app.service.responses import SuccessResponse, success_response


def get_monitor_service() -> MonitorService:
    if scheduler_state.scheduler is None:
        raise RuntimeError("The monitor scheduler has not been initialized.")
    return scheduler_state.scheduler.monitor_service


def get_dashboard_service(
    monitor_service: MonitorService = Depends(get_monitor_service),
) -> DashboardService:
    return DashboardService(
        monitor_service=monitor_service,
        monitor_result_service=monitor_service.monitor_result_service,
        incident_service=monitor_service.incident_service,
    )

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(require_viewer())])

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
