"""Linux-specific filesystem paths (XDG base directory spec)."""
from __future__ import annotations

import os
from pathlib import Path

_APP_DIR_NAME = "shared-clipboard-service"


def get_config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / _APP_DIR_NAME


def get_log_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    root = Path(base) if base else Path.home() / ".local" / "state"
    return root / _APP_DIR_NAME / "logs"


def get_received_files_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / _APP_DIR_NAME / "received"
