"""Platform adapter layer.

All OS-specific filesystem/environment logic must live in this package so
the rest of the codebase stays platform-agnostic (see CLAUDE.md: "Avoid
OS-specific code outside platform adapter modules").
"""
from __future__ import annotations

import sys

if sys.platform == "win32":
    from cbs.platform._windows import get_config_dir, get_log_dir
else:
    from cbs.platform._linux import get_config_dir, get_log_dir

__all__ = ["get_config_dir", "get_log_dir"]
