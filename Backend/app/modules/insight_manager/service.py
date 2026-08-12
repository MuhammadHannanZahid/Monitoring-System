from app.service.mongo_db.shared_models.models.base_monitor import MonitorStatus
from app.service.mongo_db.shared_models.models.dashboard import (DashboardSummaryResponse, DashboardIncidentResponse,
    DashboardActivityResponse, ResponseHistoryResponse, ResponseHistoryPoint, UptimeResponse, StatusHistoryResponse,
    StatusHistoryPoint)
from app.service.exceptions import NotFoundError
from app.service.constants import Messages
from app.service.modules.monitoring_controller.monitor_results.service import MonitorResultService
from app.service.modules.incident_manager.service import IncidentService
from app.service.modules.monitoring_controller.service import MonitorService

class DashboardService:
    def __init__(self, monitor_service: MonitorService, monitor_result_service: MonitorResultService, incident_service: IncidentService):
        self.monitor_service = monitor_service
        self.monitor_result_service = monitor_result_service
        self.incident_service = incident_service

    async def get_summary(self) -> DashboardSummaryResponse:
        monitors, _ = await self.monitor_service.get_monitors_with_lookup()
        total_monitors = len(monitors)
        active_monitors = sum(1 for monitor in monitors if monitor.is_active)
        inactive_monitors = total_monitors - active_monitors
        monitors_up = sum(1 for monitor in monitors if monitor.status == MonitorStatus.UP)
        monitors_down = sum(1 for monitor in monitors if monitor.status == MonitorStatus.DOWN)
        monitors_unknown = sum(1 for monitor in monitors if monitor.status == MonitorStatus.UNKNOWN)
        slow_monitors = sum(1 for monitor in monitors if getattr(monitor, "is_slow", False))
        open_incidents = await self.incident_service.count_open()
        average_response_time = await self.monitor_result_service.average_response_time()

        return DashboardSummaryResponse(
            total_monitors=total_monitors,
            active_monitors=active_monitors,
            inactive_monitors=inactive_monitors,
            monitors_up=monitors_up,
            monitors_down=monitors_down,
            monitors_unknown=monitors_unknown,
            open_incidents=open_incidents,
            average_response_time_ms=average_response_time,
            slow_monitors=slow_monitors,
        )

    async def get_recent_incidents(self) -> list[DashboardIncidentResponse]:
        incidents = await self.incident_service.get_recent()
        _, monitor_map = await self.monitor_service.get_monitors_with_lookup()
        results = []

        for incident in incidents:
            monitor = monitor_map.get(incident.monitor_id)

            results.append(
                DashboardIncidentResponse(
                    id=incident.id,
                    monitor_id=incident.monitor_id,
                    monitor_name=monitor.name if monitor else "Unknown",
                    started_at=incident.started_at,
                    resolved_at=incident.resolved_at,
                    duration_seconds=incident.duration_seconds,
                )
            )
        return results

    async def get_recent_activity(self) -> list[DashboardActivityResponse]:
        results = await self.monitor_result_service.get_recent()
        _, monitor_map = await self.monitor_service.get_monitors_with_lookup()
        activities = []

        for result in results:
            monitor = monitor_map.get(result.monitor_id)
            activities.append(
                DashboardActivityResponse(
                    monitor_name=monitor.name if monitor else "Unknown",
                    status=result.status,
                    status_code=result.status_code,
                    response_time_ms=result.response_time_ms,
                    checked_at=result.checked_at,
                    is_slow=result.is_slow,
                )
            )
        return activities

    async def get_response_history(self, monitor_id: str, days: int) -> ResponseHistoryResponse:
        monitor = await self.monitor_service.get_monitor(monitor_id)
        if monitor is None:
            raise NotFoundError(Messages.monitor_NOT_FOUND)

        history = await self.monitor_result_service.get_response_history(monitor_id=monitor_id, days=days)

        return ResponseHistoryResponse(
            monitor_id=monitor_id,
            points=[
                ResponseHistoryPoint(
                    checked_at=result.checked_at,
                    response_time_ms=result.response_time_ms,
                )
                for result in history
            ],
        )

    async def get_uptime(self, monitor_id: str, days: int) -> UptimeResponse:
        monitor = await self.monitor_service.get_monitor(monitor_id)

        if monitor is None:
            raise NotFoundError(Messages.monitor_NOT_FOUND)

        stats = await self.monitor_result_service.get_statistics(monitor_id=monitor_id, days=days)
        total = stats["total"]
        successful = stats["successful"]
        failed = total - successful
        uptime = (round(successful / total * 100, 2) if total > 0 else 0.0)
        slow = await self.monitor_result_service.count_slow_checks(monitor_id)

        return UptimeResponse(
            monitor_id=monitor_id,
            uptime_percentage=uptime,
            total_checks=total,
            successful_checks=successful,
            failed_checks=failed,
            slow_checks=slow,
        )

    async def get_status_history(self, monitor_id: str, days: int) -> StatusHistoryResponse:
        monitor = await self.monitor_service.get_monitor(monitor_id)

        if monitor is None:
            raise NotFoundError(Messages.monitor_NOT_FOUND)

        history = await self.monitor_result_service.get_status_history(monitor_id=monitor_id, days=days)

        return StatusHistoryResponse(
            monitor_id=monitor_id,
            history=[
                StatusHistoryPoint(
                    checked_at=result.checked_at,
                    status=result.status,
                )
                for result in history
            ],
        )