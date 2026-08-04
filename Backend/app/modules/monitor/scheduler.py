import asyncio
from app.core.logger import get_logger
from app.modules.monitor.service import MonitorService

logger = get_logger(__name__)

class MonitorScheduler:
    def __init__(self, monitor_service: MonitorService):
        self.monitor_service = monitor_service
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
        monitors = await self.monitor_service.list_active_monitors()

        tasks = [asyncio.create_task(self._check_monitor(monitor))for monitor in monitors]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_monitor(self, monitor):
        try:
            await self.monitor_service.check_and_update(
                monitor
            )

        except Exception:
            logger.exception(
                "Unexpected monitoring error for '%s'.",
                monitor.name,
            )