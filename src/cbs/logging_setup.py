"""Application logging configuration.

Logs are always written to the local machine only, never to the NAS share
(see docs/design/requirements_review_v0.1.md: the `logs` folder on the NAS
is reserved for future use and is not written to in the initial version).
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_LOGGER_NAME = "cbs"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 5
_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(log_level: str = "INFO", log_dir: Path | None = None) -> logging.Logger:
    """Configure and return the "cbs" application logger.

    Safe to call more than once (e.g. after settings are reloaded): existing
    handlers are replaced rather than stacked.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "cbs.log",
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
