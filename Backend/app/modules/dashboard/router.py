from fastapi import APIRouter, Depends
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.schemas import DashboardSummaryResponse
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