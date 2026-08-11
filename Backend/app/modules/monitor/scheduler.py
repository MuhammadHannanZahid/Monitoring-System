from app.core.logger import get_logger
from app.modules.monitor.service import MonitorService
from app.modules.monitor.worker import MonitorWorker
from app.shared.models.base_monitor import MonitorType

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
            await self.start_worker(monitor)

    async def start_worker(self, monitor) -> None:
        if (
            monitor.monitor_type == MonitorType.HEARTBEAT
            and monitor.last_heartbeat_at is None
        ):
            logger.info(
                "Heartbeat monitor '%s' is awaiting its first heartbeat.",
                monitor.name,
            )
            return

        if monitor.id in self._workers:
            return

        worker = MonitorWorker(
            monitor=monitor,
            monitor_service=self.monitor_service,
        )

        self._workers[monitor.id] = worker
        await worker.start()

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        logger.info("Stopping monitor scheduler...")
        worker_ids = list(self._workers.keys())
        for monitor_id in worker_ids:
            await self.stop_worker(monitor_id)
        logger.info("Monitor scheduler stopped.")

    async def stop_worker(self, monitor_id: str) -> None:
        worker = self._workers.pop(monitor_id, None)

        if worker is None:
            return

        await worker.stop()
