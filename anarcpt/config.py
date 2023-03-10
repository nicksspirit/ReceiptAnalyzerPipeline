import sys
from loguru import logger

logger.remove()  # Remove default loguru stderr sink

log_fmt = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | <level>{message}</level>"
)

logger.add(sys.stderr, colorize=True, format=log_fmt, backtrace=True, diagnose=True)

DB_NAME = "analyzed_receipts.db"
DB_VERBOSE_OUTPUT = False
