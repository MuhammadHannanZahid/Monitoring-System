from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from app.shared.enums import MonitorStatus, MonitorType


class HeartbeatMonitorModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    name: str
    monitor_type: Literal[MonitorType.HEARTBEAT] = MonitorType.HEARTBEAT
    expected_heartbeat_interval: int = Field(
        gt=0,
        validation_alias=AliasChoices(
            "expected_heartbeat_interval",
            "check_interval",
        ),
    )
    grace_period: int = Field(default=60, ge=0)
    heartbeat_token_hash: str
    is_active: bool = True
    status: MonitorStatus = MonitorStatus.UNKNOWN
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    last_checked_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    heartbeat_count: int = Field(default=0, ge=0)
    last_token_rotated_at: datetime | None = None
    token_expires_at: datetime | None = None
    heartbeat_token: str | None = Field(default=None, exclude=True)
