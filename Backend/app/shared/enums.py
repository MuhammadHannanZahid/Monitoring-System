from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    VIEWER = "viewer"

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"