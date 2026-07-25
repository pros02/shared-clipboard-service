"""Linux-specific filesystem paths (XDG base directory spec) and
login-startup registration (XDG autostart)."""
from __future__ import annotations

import os
import shlex
from pathlib import Path

from cbs.util.atomic_io import atomic_write_text

_APP_DIR_NAME = "shared-clipboard-service"
_DESKTOP_FILE_NAME = "shared-clipboard-service.desktop"


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


def _autostart_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "autostart"


def _autostart_file() -> Path:
    return _autostart_dir() / _DESKTOP_FILE_NAME


def enable_start_on_login(command: list[str]) -> None:
    exec_line = " ".join(shlex.quote(part) for part in command)
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Shared Clipboard Service\n"
        f"Exec={exec_line}\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    atomic_write_text(_autostart_file(), content)


def disable_start_on_login() -> None:
    _autostart_file().unlink(missing_ok=True)


def is_start_on_login_enabled() -> bool:
    return _autostart_file().exists()
