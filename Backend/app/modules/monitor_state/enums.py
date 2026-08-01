from enum import Enum

class MonitorTransition(str, Enum):
    NONE = "none"
    DOWN = "down"
    UP = "up"