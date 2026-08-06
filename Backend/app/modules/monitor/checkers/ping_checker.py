import asyncio
import aioping
from app.core.logger import get_logger
from app.modules.monitor.schemas import HealthCheckResponse
from app.shared.enums import MonitorStatus
from app.shared.models.ping_monitor import PingMonitorModel
from .base_checker import BaseChecker

logger = get_logger(__name__)

class PingChecker(BaseChecker):
    async def check(self, monitor: PingMonitorModel) -> HealthCheckResponse:
        response_time_ms = None
        success = False
        status = MonitorStatus.DOWN
        is_slow = False

        try:
            latency = await aioping.ping(monitor.host, timeout=monitor.timeout)
            response_time_ms = int(latency * 1000)
            if (monitor.expected_response_time_ms is not None and response_time_ms > monitor.expected_response_time_ms):
                is_slow = True

            success = True
            status = MonitorStatus.UP

            if is_slow:
                logger.warning("Ping monitor '%s' is UP but SLOW (%d ms > %d ms).", monitor.name, response_time_ms, monitor.expected_response_time_ms)
            else:
                logger.info("Ping monitor '%s' is UP (%d ms).", monitor.name, response_time_ms)

        except asyncio.TimeoutError:
            response_time_ms = monitor.timeout * 1000
            logger.warning("Ping monitor '%s' timed out.", monitor.name)

        except Exception as exc:
            logger.warning("Ping monitor '%s' failed: %s", monitor.name, exc)

        return HealthCheckResponse(
            url=monitor.host,
            status=status,
            status_code=None,
            response_time_ms=response_time_ms,
            success=success,
            is_slow=is_slow,
        )