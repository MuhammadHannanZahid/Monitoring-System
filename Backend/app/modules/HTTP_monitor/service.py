from datetime import datetime, timezone
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.shared.constants import Messages
from app.shared.enums import MonitorStatus
from app.shared.exceptions import ConflictError, NotFoundError
from app.shared.models.HTTP_monitor import HTTPMonitorModel
from app.core.logger import get_logger
import app.core.scheduler as scheduler_state

logger = get_logger(__name__)

class HTTP_monitorService:
    def __init__(self, repository: HTTP_monitorRepository):
        self.repository = repository

    async def create_monitor(self, name: str, url: str, check_interval: int, timeout: int, expected_status_code: int, expected_response_time_ms:int) -> HTTPMonitorModel:
        existing_url = await self.repository.get_by_url(url)
        if existing_url is not None:
            logger.warning("Attempted to create HTTP_monitor with existing URL '%s'.", url)
            raise ConflictError(Messages.HTTP_monitor_ALREADY_EXISTS)

        count = await self.repository.count_similar_names(name)
        final_name = name

        if count > 0:
            final_name = f"{name} {count}"
            logger.info("HTTP_monitor name '%s' already exists. Assigned new name '%s'.", name, final_name)

        now = datetime.now(timezone.utc)

        HTTP_monitor = HTTPMonitorModel(
            name=final_name,
            url=url,
            check_interval=check_interval,
            timeout=timeout,
            expected_status_code=expected_status_code,
            status=MonitorStatus.UNKNOWN,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_checked_at=None,
            expected_response_time_ms=expected_response_time_ms,
        )

        HTTP_monitor.id = await self.repository.create(HTTP_monitor)
        logger.info("HTTP_monitor '%s' created. URL: %s", HTTP_monitor.name, HTTP_monitor.url)
        return HTTP_monitor

    async def list_monitors(self) -> list[HTTPMonitorModel]:
        return await self.repository.list_monitors()

    async def get_monitor(self, HTTP_monitor_id: str) -> HTTPMonitorModel:
        HTTP_monitor = await self.repository.get_by_id(HTTP_monitor_id)
        if HTTP_monitor is None:
            logger.warning("Requested HTTP_monitor '%s' was not found.", HTTP_monitor_id)
            raise NotFoundError(Messages.monitor_NOT_FOUND)
        return HTTP_monitor

    async def update_monitor(self, HTTP_monitor_id: str, name: str | None, url: str | None, check_interval: int | None, timeout: int | None, expected_status_code: int | None, expected_response_time_ms:int) -> HTTPMonitorModel:
        HTTP_monitor = await self.get_monitor(HTTP_monitor_id)
        update_data = {}
        if name is not None and name != HTTP_monitor.name:
            count = await self.repository.count_similar_names(name)
            if count > 0:
                final_name = f"{name} {count}"
                logger.info("HTTP_monitor name '%s' already exists. Assigned new name '%s' during update for HTTP_monitor ID %s.", name, final_name, HTTP_monitor_id)
                update_data["name"] = final_name
            else:
                update_data["name"] = name

        if url is not None and url != HTTP_monitor.url:
            existing_url = await self.repository.get_by_url(url)
            if existing_url is not None and str(existing_url.id) != str(HTTP_monitor_id):
                logger.warning("Attempted to update HTTP_monitor '%s' with existing URL '%s'.", HTTP_monitor.name, url)
                raise ConflictError(Messages.HTTP_monitor_ALREADY_EXISTS)
            update_data["url"] = url

        if check_interval is not None and check_interval != HTTP_monitor.check_interval:
            update_data["check_interval"] = check_interval

        if timeout is not None and timeout != HTTP_monitor.timeout:
            update_data["timeout"] = timeout

        if expected_status_code is not None and expected_status_code != HTTP_monitor.expected_status_code:
            update_data["expected_status_code"] = expected_status_code

        if expected_response_time_ms is not None and expected_response_time_ms != HTTP_monitor.expected_response_time_ms:
            update_data["expected_response_time_ms"] = expected_response_time_ms

        if update_data:
            await self.repository.update_monitor(HTTP_monitor_id, update_data)
            updated_HTTP_monitor = await self.get_monitor(HTTP_monitor_id)
            logger.info("HTTP_monitor '%s' updated. Fields changed: %s", updated_HTTP_monitor.name, ", ".join(update_data.keys()))
            return updated_HTTP_monitor

        return HTTP_monitor

    async def delete_monitor(self, HTTP_monitor_id: str) -> None:
        HTTP_monitor = await self.get_monitor(HTTP_monitor_id)
        await self.repository.delete_monitor(HTTP_monitor.id)
        logger.info("HTTP_monitor '%s' deleted.", HTTP_monitor.name)

    async def activate_monitor(self, HTTP_monitor_id: str):
        monitor = await self.get_monitor(HTTP_monitor_id)
        await self.repository.set_active(monitor.id, True)
        updated = await self.get_monitor(HTTP_monitor_id)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.start_worker(updated)
        return updated

    async def deactivate_monitor(self, HTTP_monitor_id: str):
        monitor = await self.get_monitor(HTTP_monitor_id)
        await self.repository.set_active(monitor.id, False)
        if scheduler_state.scheduler is not None:
            await scheduler_state.scheduler.stop_worker(monitor.id)
        return await self.get_monitor(HTTP_monitor_id)