from app.shared.enums import HTTP_monitorStatus
from app.modules.dashboard.schemas import (DashboardSummaryResponse, DashboardMonitorResponse, DashboardIncidentResponse,
    DashboardActivityResponse, ResponseHistoryResponse, ResponseHistoryPoint, UptimeResponse, StatusHistoryResponse,
    StatusHistoryPoint)
from app.shared.exceptions import NotFoundError
from app.shared.constants import Messages
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.modules.monitor_results.repository import MonitorResultRepository
from app.modules.incident.repository import IncidentRepository
from app.modules.API_monitor.repository import API_monitorRepository

class DashboardService:
    def __init__(self, HTTP_monitor_repository: HTTP_monitorRepository, API_monitor_repository: API_monitorRepository, monitor_result_repository: MonitorResultRepository, incident_repository: IncidentRepository):
        self.monitor_repository = HTTP_monitor_repository
        self.API_monitor_repository = API_monitor_repository
        self.monitor_result_repository = monitor_result_repository
        self.incident_repository = incident_repository

    async def get_summary(self) -> DashboardSummaryResponse:
        http_count = await self.monitor_repository.count_all()
        api_count = await self.API_monitor_repository.count_all()

        total_monitors = http_count + api_count
        active_monitors = await self.monitor_repository.count_active()
        inactive_monitors = await self.monitor_repository.count_inactive()
        monitors_up = await self.monitor_repository.count_by_status(HTTP_monitorStatus.UP)
        monitors_down = await self.monitor_repository.count_by_status(HTTP_monitorStatus.DOWN)
        monitors_unknown = await self.monitor_repository.count_by_status(HTTP_monitorStatus.UNKNOWN)
        open_incidents = await self.incident_repository.count_open()
        average_response_time = (await self.monitor_result_repository.average_response_time())

        return DashboardSummaryResponse(
            total_monitors=total_monitors,
            active_monitors=active_monitors,
            inactive_monitors=inactive_monitors,
            monitors_up=monitors_up,
            monitors_down=monitors_down,
            monitors_unknown=monitors_unknown,
            open_incidents=open_incidents,
            average_response_time_ms=average_response_time,
        )

    async def get_monitors(self) -> list[DashboardMonitorResponse]:
        HTTP_monitors = await self.monitor_repository.list_monitors()

        responses = []

        for monitor in HTTP_monitors:
            stats = await self.monitor_result_repository.get_statistics(
                monitor_id=monitor.id,
                days=30,
            )

            total = stats["total"]
            successful = stats["successful"]

            uptime = (
                round(successful / total * 100, 2)
                if total > 0
                else 0.0
            )

            incidents = len(
                await self.incident_repository.list_by_monitor(monitor.id)
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
        HTTP_monitors = await self.monitor_repository.list_monitors()
        HTTP_monitor_map = {
            HTTP_monitor.id: HTTP_monitor
            for HTTP_monitor in HTTP_monitors
        }

        results = []
        for incident in incidents:
            HTTP_monitor = HTTP_monitor_map.get(incident.monitor_id)

            results.append(
                DashboardIncidentResponse(
                    id=incident.id,
                    monitor_id=incident.monitor_id,
                    monitor_name=HTTP_monitor.name if HTTP_monitor else "Unknown",
                    started_at=incident.started_at,
                    resolved_at=incident.resolved_at,
                    duration_seconds=incident.duration_seconds,
                )
            )

        return results

    async def get_recent_activity(self) -> list[DashboardActivityResponse]:
        results = await self.monitor_result_repository.get_recent()
        HTTP_monitors = await self.monitor_repository.list_monitors()

        HTTP_monitor_map = {
            HTTP_monitor.id: HTTP_monitor
            for HTTP_monitor in HTTP_monitors
        }

        activities = []
        for result in results:
            HTTP_monitor = HTTP_monitor_map.get(result.monitor_id)

            activities.append(
                DashboardActivityResponse(
                    monitor_name=HTTP_monitor.name if HTTP_monitor else "Unknown",
                    status=result.status,
                    status_code=result.status_code,
                    response_time_ms=result.response_time_ms,
                    checked_at=result.checked_at,
                )
            )

        return activities

    async def get_response_history(self, monitor_id: str, days: int) -> ResponseHistoryResponse:
        HTTP_monitor = await self.monitor_repository.get_by_id(monitor_id)

        if HTTP_monitor is None:
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
        HTTP_monitor = await self.monitor_repository.get_by_id(monitor_id)

        if HTTP_monitor is None:
            raise NotFoundError(Messages.monitor_NOT_FOUND)

        stats = await self.monitor_result_repository.get_statistics(monitor_id=monitor_id, days=days)
        total = stats["total"]
        successful = stats["successful"]
        failed = total - successful
        uptime = (round(successful / total * 100, 2) if total > 0 else 0.0)

        return UptimeResponse(
            monitor_id=monitor_id,
            uptime_percentage=uptime,
            total_checks=total,
            successful_checks=successful,
            failed_checks=failed,
        )

    async def get_status_history(self, monitor_id: str, days: int) -> StatusHistoryResponse:
        HTTP_monitor = await self.monitor_repository.get_by_id(monitor_id)

        if HTTP_monitor is None:
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