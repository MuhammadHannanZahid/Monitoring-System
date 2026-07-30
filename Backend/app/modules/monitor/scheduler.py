import asyncio
from app.core.logger import get_logger
from app.modules.monitor.service import MonitorService
from app.modules.website.service import WebsiteService

logger = get_logger(__name__)

class MonitorScheduler:
    def __init__(self, monitor_service: MonitorService, website_service: WebsiteService):
        self.monitor_service = monitor_service
        self.website_service = website_service
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
        websites = await self.website_service.list_websites()
        for website in websites:
            if not website.is_active:
                continue

            try:
                await self.monitor_service.check_and_update(website)

            except Exception:
                logger.exception("Unexpected monitoring error for '%s'.", website.name)