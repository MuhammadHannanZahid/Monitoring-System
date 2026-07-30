import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

APP_LOG_FILE = LOG_DIR / "app.log"
ERROR_LOG_FILE = LOG_DIR / "error.log"

LOG_FORMAT = ("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

class MaxLevelFilter(logging.Filter):
    def __init__(self, level: int):
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.level

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT,)

root_logger = logging.getLogger()

root_logger.setLevel(settings.log_level.upper())

root_logger.propagate = False

if root_logger.handlers:
    root_logger.handlers.clear()

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(settings.log_level.upper())

app_handler = RotatingFileHandler(
    APP_LOG_FILE,
    maxBytes=10 * 1024 * 1024,
    backupCount=10,
    encoding="utf-8",
)

app_handler.setFormatter(formatter)
app_handler.setLevel(settings.log_level.upper())
app_handler.addFilter(MaxLevelFilter(logging.WARNING))

error_handler = RotatingFileHandler(
    ERROR_LOG_FILE,
    maxBytes=10 * 1024 * 1024,
    backupCount=10,
    encoding="utf-8",
)

error_handler.setFormatter(formatter)
error_handler.setLevel(logging.ERROR)

root_logger.addHandler(console_handler)
root_logger.addHandler(app_handler)
root_logger.addHandler(error_handler)

httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)
httpx_logger.propagate = False

httpcore_logger = logging.getLogger("httpcore")
httpcore_logger.setLevel(logging.WARNING)
httpcore_logger.propagate = False

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)