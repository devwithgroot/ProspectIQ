from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv


LOGGER_NAME = "prospectiq"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "research.log"

_configured = False
_announced = False


class FlushingStreamHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


class QuietAccessFilter(logging.Filter):
    """Hide routine poll / health hits so research errors stay visible."""

    _skip_prefixes = (
        "GET /health",
        "GET /api/catalog",
        "GET /api/mock/bundle",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if any(token in message for token in self._skip_prefixes):
            return False
        if "GET /api/research/" in message and " 200 " in message:
            return False
        return True


def configure_logging() -> logging.Logger:
    global _configured, _announced
    load_dotenv()

    logger = logging.getLogger(LOGGER_NAME)
    logger.disabled = False
    logger.propagate = False

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not _configured or not logger.handlers:
        logger.handlers.clear()

        console = FlushingStreamHandler(sys.stderr)
        console.setLevel(level)
        console.setFormatter(formatter)

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)

        logger.addHandler(console)
        logger.addHandler(file_handler)
        _configured = True
    else:
        for handler in logger.handlers:
            handler.setLevel(level)

    quiet_access_logs()

    if not _announced:
        logger.info("Research logging on → terminal + %s (level=%s)", LOG_FILE, level_name)
        _announced = True
    return logger


def quiet_access_logs() -> None:
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, QuietAccessFilter) for item in access.filters):
        access.addFilter(QuietAccessFilter())


def get_logger(suffix: str | None = None) -> logging.Logger:
    configure_logging()
    if suffix:
        child = logging.getLogger(f"{LOGGER_NAME}.{suffix}")
        child.disabled = False
        return child
    return logging.getLogger(LOGGER_NAME)
