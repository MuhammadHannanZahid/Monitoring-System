import asyncio
import aioping
from app.core.logger import get_logger
from app.modules.monitor.checkers.base_checker import BaseChecker
from app.modules.monitor.checkers.models import CheckResult
from app.shared.enums import MonitorStatus

logger = get_logger(__name__)

class PingChecker(BaseChecker):
    async def check(self, monitor) -> CheckResult:
        response_time_ms = None
        is_slow = False

        try:
            latency = await aioping.ping(monitor.host, timeout=monitor.timeout)
            response_time_ms = round(latency * 1000)
            is_slow = monitor.expected_response_time_ms is not None and response_time_ms > monitor.expected_response_time_ms

            if is_slow:
                logger.warning("Ping monitor '%s' is UP but SLOW (%d ms > %d ms).", monitor.name, response_time_ms, monitor.expected_response_time_ms)
            else:
                logger.info("Ping monitor '%s' is UP (%d ms).", monitor.name, response_time_ms)

            return CheckResult(
                success=True,
                status=MonitorStatus.UP,
                status_code=None,
                response_time_ms=response_time_ms,
                is_slow=is_slow,
            )
        except asyncio.TimeoutError:
            logger.warning("Ping timed out for '%s' after '%d'.", monitor.name, monitor.timeout * 1000)

            return CheckResult(
                success=False,
                status=MonitorStatus.DOWN,
                status_code=None,
                response_time_ms=monitor.timeout * 1000,
                is_slow=True,
            )
        except Exception:
            logger.exception("Ping monitor '%s' failed.", monitor.name)

            return CheckResult(
                success=False,
                status=MonitorStatus.DOWN,
                status_code=None,
                response_time_ms=monitor.timeout * 1000,
                is_slow=True,
            )