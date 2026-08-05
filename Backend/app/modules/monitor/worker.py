import asyncio
from app.core.logger import get_logger
from app.shared.models.base_monitor import BaseMonitorModel
from app.modules.monitor.service import MonitorService

logger = get_logger(__name__)

class MonitorWorker:
    def __init__(
        self,
        monitor: BaseMonitorModel,
        monitor_service: MonitorService,
    ):
        self.monitor = monitor
        self.monitor_service = monitor_service

        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run())

        logger.info(
            "Started worker for '%s'.",
            self.monitor.name,
        )

    async def stop(self) -> None:
        self._running = False

        if self._task:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info(
            "Stopped worker for '%s'.",
            self.monitor.name,
        )

    async def _run(self) -> None:
        while self._running:
            start = asyncio.get_running_loop().time()

            try:
                await self.monitor_service.check_and_update(
                    self.monitor
                )
            except Exception:
                logger.exception(
                    "Worker failed for '%s'.",
                    self.monitor.name,
                )

            elapsed = (
                asyncio.get_running_loop().time()
                - start
            )

            sleep_time = max(
                0,
                self.monitor.check_interval - elapsed,
            )

            await asyncio.sleep(sleep_time)