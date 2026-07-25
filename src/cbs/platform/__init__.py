"""Platform adapter layer.

All OS-specific filesystem/environment logic must live in this package so
the rest of the codebase stays platform-agnostic (see CLAUDE.md: "Avoid
OS-specific code outside platform adapter modules").
"""
from __future__ import annotations

import sys

if sys.platform == "win32":
    from cbs.platform._windows import (
        disable_start_on_login,
        enable_start_on_login,
        get_config_dir,
        get_log_dir,
        get_received_files_dir,
        is_start_on_login_enabled,
    )
else:
    from cbs.platform._linux import (
        disable_start_on_login,
        enable_start_on_login,
        get_config_dir,
        get_log_dir,
        get_received_files_dir,
        is_start_on_login_enabled,
    )

__all__ = [
    "disable_start_on_login",
    "enable_start_on_login",
    "get_config_dir",
    "get_log_dir",
    "get_received_files_dir",
    "is_start_on_login_enabled",
]
