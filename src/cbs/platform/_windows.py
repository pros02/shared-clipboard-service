"""Windows-specific filesystem paths and login-startup registration."""
from __future__ import annotations

import os
import subprocess
import winreg
from pathlib import Path

_APP_DIR_NAME = "SharedClipboardService"
_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE_NAME = "SharedClipboardService"


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


def enable_start_on_login(command: list[str]) -> None:
    command_line = subprocess.list2cmdline(command)
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
        winreg.SetValueEx(key, _RUN_VALUE_NAME, 0, winreg.REG_SZ, command_line)


def disable_start_on_login() -> None:
    try:
        with winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _RUN_VALUE_NAME)
    except FileNotFoundError:
        pass


def is_start_on_login_enabled() -> bool:
    try:
        with winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_QUERY_VALUE) as key:
            winreg.QueryValueEx(key, _RUN_VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
