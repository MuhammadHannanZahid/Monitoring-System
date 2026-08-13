import asyncio
from datetime import datetime, timedelta, timezone
from app.core.logger import get_logger
from app.modules.monitoring_controller.monitoring_controller import MonitorManager
from app.service.mongo_db.shared_models.db_monitoring_controller_model import MonitorType
from app.service.mongo_db.shared_models.db_monitoring_controller_model import BaseMonitorModel
from app.service.mongo_db.shared_models.db_heartbeat_monitor_model import HeartbeatMonitorModel

logger = get_logger(__name__)

MonitorModel = BaseMonitorModel | HeartbeatMonitorModel

class MonitorWorker:
    def __init__(self, monitor: MonitorModel, monitor_service: MonitorManager):
        self.monitor = monitor
        self.monitor_service = monitor_service

        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run())

        logger.info("Started worker for '%s'.", self.monitor.name)

    async def stop(self) -> None:
        self._running = False

        if self._task:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped worker for '%s'.", self.monitor.name)

    async def _run(self) -> None:
        if self.monitor.monitor_type == MonitorType.HEARTBEAT:
            await self._run_heartbeat()
            return

        while self._running:
            start = asyncio.get_running_loop().time()
            try:
                monitor = await self.monitor_service.get_monitor(
                    self.monitor.id,
                    self.monitor.monitor_type,
                )
                if monitor is None:
                    logger.info("Monitor '%s' removed. Worker stopping.", self.monitor.id)
                    break

                self.monitor = monitor
                await self.monitor_service.check_and_update(self.monitor)
            except asyncio.CancelledError:
                break

            except Exception:
                logger.exception("Worker failed for '%s'.", self.monitor.name)

            elapsed = asyncio.get_running_loop().time() - start
            sleep_time = max(0, self.monitor.check_interval - elapsed)
            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break

        self._running = False

    async def _run_heartbeat(self) -> None:
        while self._running:
            try:
                monitor = await self.monitor_service.get_monitor(
                    self.monitor.id,
                    self.monitor.monitor_type,
                )
                if monitor is None:
                    logger.info("Heartbeat monitor '%s' removed. Worker stopping.", self.monitor.id)
                    break

                if not isinstance(monitor, HeartbeatMonitorModel):
                    logger.error("Monitor '%s' was registered as heartbeat with an incompatible model.", self.monitor.id)
                    break

                if monitor.last_heartbeat_at is None:
                    logger.info("Heartbeat monitor '%s' is awaiting its first heartbeat. Worker stopping.", monitor.name)
                    break

                self.monitor = monitor
                sleep_seconds = self._seconds_until_heartbeat_deadline(monitor)
                if sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)
                    continue

                await self.monitor_service.check_and_update(monitor)
                await asyncio.sleep(monitor.expected_heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Heartbeat worker failed for '%s'.", self.monitor.name)
        self._running = False

    @staticmethod
    def _seconds_until_heartbeat_deadline(monitor: HeartbeatMonitorModel) -> float:
        if monitor.last_heartbeat_at is None:
            raise ValueError("A heartbeat deadline is unavailable before the first heartbeat.")
        deadline = monitor.last_heartbeat_at + timedelta(seconds=monitor.expected_heartbeat_interval + monitor.grace_period)
        return max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds())
