from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    VIEWER = "viewer"

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"

class HTTP_monitorStatus(str, Enum):
    UNKNOWN = "unknown"
    UP = "up"
    DOWN = "down"

class MonitorType(str, Enum):
    HTTP = "HTTP"
    API = "API"