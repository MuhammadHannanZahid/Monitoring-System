from app.shared.enums import MonitorStatus
from app.modules.dashboard.schemas import (DashboardSummaryResponse, DashboardMonitorResponse, DashboardIncidentResponse,
    DashboardActivityResponse, ResponseHistoryResponse, ResponseHistoryPoint, UptimeResponse, StatusHistoryResponse,
    StatusHistoryPoint)
from app.shared.exceptions import NotFoundError
from app.shared.constants import Messages
from app.modules.monitor_results.repository import MonitorResultRepository
from app.modules.incident.repository import IncidentRepository
from app.modules.monitor.service import MonitorService

class DashboardService:
    def __init__(self, monitor_service: MonitorService, monitor_result_repository: MonitorResultRepository, incident_repository: IncidentRepository):
        self.monitor_service = monitor_service
        self.monitor_result_repository = monitor_result_repository
        self.incident_repository = incident_repository

    async def get_summary(self) -> DashboardSummaryResponse:
        monitors = await self.monitor_service.get_monitors_with_lookup()
        total_monitors = len(monitors)
        active_monitors = sum(1 for monitor in monitors if monitor.is_active)
        inactive_monitors = total_monitors - active_monitors
        monitors_up = sum(1 for monitor in monitors if monitor.status == MonitorStatus.UP)
        monitors_down = sum(1 for monitor in monitors if monitor.status == MonitorStatus.DOWN)
        monitors_unknown = sum(1 for monitor in monitors if monitor.status == MonitorStatus.UNKNOWN)
        slow_monitors = sum(1 for monitor in monitors if getattr(monitor, "is_slow", False))
        open_incidents = await self.incident_repository.count_open()
        average_response_time = await self.monitor_result_repository.average_response_time()

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

    async def get_monitors(self) -> list[DashboardMonitorResponse]:
        monitors = await self.monitor_service.get_monitors_with_lookup()
        total = len(monitors)
        responses = []

        for monitor in monitors:
            stats = stats_lookup.get(
                monitor.id,
                {
                    "total": 0,
                    "successful": 0,
                },
            )

            total = stats["total"]
            successful = stats["successful"]

            uptime = (
                round(successful / total * 100, 2)
                if total > 0
                else 0.0
            )

            incidents = incident_lookup.get(
                monitor.id,
                0,
            )

            responses.append(
                DashboardMonitorResponse(
                    id=monitor.id,
                    name=monitor.name,
                    url=monitor.url,
                    status=monitor.status,
                    response_time_ms=monitor.last_response_time_ms,
                    status_code=monitor.last_status_code,
                    uptime_percentage=uptime,
                    incidents=incidents,
                    last_checked_at=monitor.last_checked_at,
                    is_active=monitor.is_active,
                )
            )

        return responses

    async def get_recent_incidents(self) -> list[DashboardIncidentResponse]:

        incidents = await self.incident_repository.get_recent()

        monitor_map = await self.monitor_service.get_monitors_with_lookup()

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

        results = await self.monitor_result_repository.get_recent()

        monitor_map = await self.monitor_service.get_monitors_with_lookup()

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

        history = await self.monitor_result_repository.get_response_history(monitor_id=monitor_id, days=days)

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
        monitor = await self.monitor_service.get_monitor(
            monitor_id
        )

        if monitor is None:
            raise NotFoundError(Messages.monitor_NOT_FOUND)

        stats = await self.monitor_result_repository.get_statistics(monitor_id=monitor_id, days=days)
        total = stats["total"]
        successful = stats["successful"]
        failed = total - successful
        uptime = (round(successful / total * 100, 2) if total > 0 else 0.0)
        slow = await self.monitor_result_repository.count_slow_checks(monitor_id)

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

        history = await self.monitor_result_repository.get_status_history(monitor_id=monitor_id, days=days)

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