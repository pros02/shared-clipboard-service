from __future__ import annotations

import logging
from pathlib import Path

from cbs.logging_setup import configure_logging


def test_configure_logging_creates_log_file(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"

    logger = configure_logging("DEBUG", log_dir)
    logger.info("hello")
    for handler in logger.handlers:
        handler.flush()

    assert (log_dir / "cbs.log").exists()
    assert logger.level == logging.DEBUG


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"

    configure_logging("INFO", log_dir)
    logger = configure_logging("INFO", log_dir)

    assert len(logger.handlers) == 2


def test_configure_logging_without_log_dir_only_adds_console_handler(tmp_path: Path) -> None:
    logger = configure_logging("INFO", None)

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
