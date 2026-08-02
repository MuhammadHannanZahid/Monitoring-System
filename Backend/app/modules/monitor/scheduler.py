import asyncio
from app.core.logger import get_logger
from app.modules.monitor.service import MonitorService
from app.modules.HTTP_monitor.service import HTTP_monitorService

logger = get_logger(__name__)

class MonitorScheduler:
    def __init__(self, monitor_service: MonitorService, HTTP_monitor_service: HTTP_monitorService):
        self.monitor_service = monitor_service
        self.HTTP_monitor_service = HTTP_monitor_service
        self._running = False

    async def start(self):
        if self._running:
            return

        self._running = True
        logger.info("Monitor scheduler started.")

        while self._running:
            await self.run_cycle()
            await asyncio.sleep(5)

    async def stop(self):
        self._running = False
        logger.info("Monitor scheduler stopped.")

    async def run_cycle(self):
        monitors = await self.HTTP_monitor_service.list_monitors()

        for monitor in monitors:
            if not monitor.is_active:
                continue
            try:
                await self.monitor_service.check_and_update(monitor)
            except Exception:
                logger.exception("Unexpected monitoring error for '%s'.", monitor.name)