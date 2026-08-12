from dataclasses import dataclass
from datetime import datetime, timezone
from app.core.logger import get_logger
from app.service.mongo_db.shared_models.db_monitoring_controller_model import MonitorStatus
from app.service.mongo_db.shared_models.db_heartbeat_monitor_model import HeartbeatMonitorModel

logger = get_logger(__name__)

@dataclass(frozen=True)
class HeartbeatCheckResult:
    status: MonitorStatus
    success: bool
    status_code: None = None
    response_time_ms: None = None
    is_slow: bool = False

class HeartbeatChecker:
    async def check(self, monitor: HeartbeatMonitorModel) -> HeartbeatCheckResult:
        now = datetime.now(timezone.utc)
        allowed_seconds = monitor.expected_heartbeat_interval + monitor.grace_period

        if monitor.last_heartbeat_at is None:
            return HeartbeatCheckResult(
                success=False,
                status=MonitorStatus.UNKNOWN,
            )

        elapsed_seconds = (now - monitor.last_heartbeat_at).total_seconds()
        success = elapsed_seconds <= allowed_seconds
        status = MonitorStatus.UP if success else MonitorStatus.DOWN

        if not success:
            logger.warning("Heartbeat '%s' is DOWN", monitor.name)

        return HeartbeatCheckResult(
            status=status,
            success=success,
        )

    async def close(self) -> None:
        pass