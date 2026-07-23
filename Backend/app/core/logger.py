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

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s | %(message)s"
)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT,)

logger = logging.getLogger()

logger.setLevel(settings.log_level.upper())

logger.propagate = False

if logger.handlers:
    logger.handlers.clear()

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

error_handler = RotatingFileHandler(
    ERROR_LOG_FILE,
    maxBytes=10 * 1024 * 1024,
    backupCount=10,
    encoding="utf-8",
)

error_handler.setFormatter(formatter)
error_handler.setLevel(logging.ERROR)

logger.addHandler(console_handler)
logger.addHandler(app_handler)
logger.addHandler(error_handler)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)