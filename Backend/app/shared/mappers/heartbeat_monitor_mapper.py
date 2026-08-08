from app.shared.models.heartbeat_monitor import HeartbeatMonitorModel
from app.modules.heartbeat_monitor.schemas import (
    HeartbeatMonitorResponse,
    HeartbeatTokenResponse,
    RegenerateHeartbeatTokenResponse,
)


class HeartbeatMonitorMapper:

    @staticmethod
    def to_response(
        monitor: HeartbeatMonitorModel,
    ) -> HeartbeatMonitorResponse:
        return HeartbeatMonitorResponse(
            id=monitor.id,
            name=monitor.name,
            expected_heartbeat_interval=monitor.expected_heartbeat_interval,
            grace_period=monitor.grace_period,
            status=monitor.status.value,
            is_active=monitor.is_active,
            last_heartbeat_at=(
                monitor.last_heartbeat_at.isoformat()
                if monitor.last_heartbeat_at
                else None
            ),
            created_at=monitor.created_at.isoformat(),
            updated_at=monitor.updated_at.isoformat(),
        )

    @staticmethod
    def to_response_list(
        monitors: list[HeartbeatMonitorModel],
    ) -> list[HeartbeatMonitorResponse]:
        return [
            HeartbeatMonitorMapper.to_response(m)
            for m in monitors
        ]

    @staticmethod
    def to_token_response(
        monitor: HeartbeatMonitorModel,
    ) -> HeartbeatTokenResponse:
        return HeartbeatTokenResponse(
            heartbeat_token=monitor.heartbeat_token,
        )

    @staticmethod
    def to_regenerated_token_response(
        monitor: HeartbeatMonitorModel,
    ) -> RegenerateHeartbeatTokenResponse:
        return RegenerateHeartbeatTokenResponse(
            heartbeat_token=monitor.heartbeat_token,
        )
