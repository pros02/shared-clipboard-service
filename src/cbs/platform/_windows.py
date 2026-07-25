"""Windows-specific filesystem paths."""
from __future__ import annotations

import os
from pathlib import Path

_APP_DIR_NAME = "SharedClipboardService"


def get_config_dir() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    return root / _APP_DIR_NAME


def get_log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / _APP_DIR_NAME / "logs"


def get_received_files_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / _APP_DIR_NAME / "received"
