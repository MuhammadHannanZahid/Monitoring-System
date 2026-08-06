from datetime import datetime, timezone
from app.core.logger import get_logger
from app.modules.monitor.schemas import HealthCheckResponse
from app.shared.enums import MonitorStatus
from app.shared.models.heartbeat_monitor import HeartbeatMonitorModel
from .base_checker import BaseChecker

logger = get_logger(__name__)

class HeartbeatChecker(BaseChecker):
    async def check(self, monitor: HeartbeatMonitorModel) -> HealthCheckResponse:
        now = datetime.now(timezone.utc)

        if monitor.last_heartbeat_at is None:
            logger.warning("Heartbeat monitor '%s' has never received a heartbeat.", monitor.name)

            return HealthCheckResponse(
                success=False,
                status=MonitorStatus.DOWN,
                status_code=None,
                response_time_ms=1000,
                is_slow=False,
                timed_out=True,
                error="Request timed out.",
            )

        elapsed_ms = int((now - monitor.last_heartbeat_at).total_seconds() * 1000)
        allowed_ms = (monitor.check_interval + monitor.grace_period) * 1000
        success = elapsed_ms <= allowed_ms
        status = MonitorStatus.UP if success else MonitorStatus.DOWN
        is_slow = False
        if monitor.expected_response_time_ms is not None and elapsed_ms > monitor.expected_response_time_ms:
            is_slow = True
            logger.warning("Heartbeat monitor '%s' is UP but SLOW (%d ms > %d ms).", monitor.name, elapsed_ms, monitor.expected_response_time_ms)

        if success:
            logger.info("Heartbeat '%s' is UP (%d ms since last beat).", monitor.name, elapsed_ms)
        else:
            logger.warning("Heartbeat '%s' is DOWN (%d ms since last beat, allowed %d ms).", monitor.name, elapsed_ms, allowed_ms)

        return HealthCheckResponse(
            url=None,
            status=status,
            status_code=None,
            response_time_ms=elapsed_ms,
            success=success,
            is_slow=is_slow,
        )