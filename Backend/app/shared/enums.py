from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    VIEWER = "viewer"

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"

class MonitorStatus(str, Enum):
    UNKNOWN = "unknown"
    UP = "up"
    DOWN = "down"

class MonitorType(str, Enum):
    HTTP = "HTTP"
    API = "API"
    PING = "ping"
    HEARTBEAT = "heartbeat"

class PerformanceStatus(str, Enum):
    UNKNOWN = "unknown"
    FAST = "fast"
    SLOW = "slow"
    NOT_CHECKED = "not_checked"