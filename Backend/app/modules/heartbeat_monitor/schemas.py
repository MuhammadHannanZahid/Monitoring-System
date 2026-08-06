from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class CreateHeartbeatMonitorRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    check_interval: int = Field(..., gt=0)
    grace_period: int = Field(..., ge=0)
    expected_response_time_ms: int | None = Field(default=None, gt=0)

class UpdateHeartbeatMonitorRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    check_interval: int | None = Field(default=None, gt=0)
    grace_period: int | None = Field(default=None, ge=0)
    expected_response_time_ms: int | None = Field(default=None, gt=0)

class HeartbeatMonitorResponse(BaseModel):
    id: str
    name: str
    check_interval: int
    grace_period: int
    status: str
    is_active: bool
    expected_response_time_ms: int | None
    last_heartbeat_at: str | None
    created_at: str
    updated_at: str
    model_config = ConfigDict(from_attributes=True)

class HeartbeatTokenResponse(BaseModel):
    heartbeat_token: str
    model_config = ConfigDict(from_attributes=True)

class RegenerateHeartbeatTokenResponse(BaseModel):
    heartbeat_token: str

class HeartbeatResponse(BaseModel):
    message: str
    next_heartbeat_in: int
    server_time: datetime
    token_rotation_required: bool