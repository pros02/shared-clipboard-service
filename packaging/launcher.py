"""PyInstaller entry point.

PyInstaller needs an actual .py script to analyze (not a `-m module`
target), so this is a thin wrapper around the real entry point.
"""
from __future__ import annotations

from cbs.gui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
