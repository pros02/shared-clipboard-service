"""PySide6 GUI layer.

Contains presentation only; business rules live in cbs.app/cbs.storage
(see CLAUDE.md: "do not put business logic directly in GUI classes").
`cbs.gui.app.main()` is the composition root that wires everything
together and shows `MainWindow`.
"""
from __future__ import annotations

from cbs.gui.main_window import MainWindow

__all__ = ["MainWindow"]
