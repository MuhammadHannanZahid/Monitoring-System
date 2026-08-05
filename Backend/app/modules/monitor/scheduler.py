import asyncio
from app.core.logger import get_logger
from app.modules.monitor.service import MonitorService
from app.modules.monitor.worker import MonitorWorker

logger = get_logger(__name__)

class MonitorScheduler:
    def __init__(self, monitor_service: MonitorService):
        self.monitor_service = monitor_service
        self._running = False
        self._workers: dict[str, MonitorWorker] = {}

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("Monitor scheduler started.")
        monitors = await self.monitor_service.list_active_monitors()
        for monitor in monitors:
            worker = MonitorWorker(monitor=monitor, monitor_service=self.monitor_service)
            self._workers[monitor.id] = worker
            await worker.start()

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        logger.info("Stopping monitor scheduler...")
        workers = list(self._workers.values())
        for worker in workers:
            await worker.stop()
        self._workers.clear()
        logger.info("Monitor scheduler stopped.")