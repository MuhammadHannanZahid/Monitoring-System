import asyncio
from app.core.logger import get_logger
from app.shared.models.base_monitor import HealthCheckResponse, MonitorStatus
from app.shared.models.ping_monitor import PingMonitorModel
import re

logger = get_logger(__name__)

class PingChecker:
    async def check(self, monitor: PingMonitorModel) -> HealthCheckResponse:
        response_time_ms = None
        success = False
        status = MonitorStatus.DOWN
        is_slow = False
        try:
            process = await asyncio.create_subprocess_exec(
                "ping",
                "-c", "1",
                "-W", str(monitor.timeout),
                monitor.host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode()
                match = re.search(r"time=([\d.]+)", output)

                if match:
                    response_time_ms = int(float(match.group(1)))
                else:
                    response_time_ms = None

                success = True
                status = MonitorStatus.UP

                if response_time_ms is not None and monitor.expected_response_time_ms is not None and response_time_ms > monitor.expected_response_time_ms:
                    is_slow = True

                if is_slow:
                    logger.warning("Ping monitor '%s' is UP but SLOW (%d ms > %d ms).", monitor.name, response_time_ms, monitor.expected_response_time_ms)
                else:
                    logger.info("Ping monitor '%s' is UP (%d ms).", monitor.name, response_time_ms)
            else:
                logger.warning("Ping monitor '%s' failed: %s", monitor.name, stderr.decode().strip())

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

    async def close(self) -> None:
        return None
