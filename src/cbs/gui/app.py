"""GUI bootstrap: composition root for the desktop application.

Loads settings, configures logging, constructs the clipboard adapter,
and shows the main window. This is the one place allowed to wire
concrete implementations together; MainWindow itself only depends on
the abstractions (ClipboardAdapter, ClipboardService).
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from cbs import platform
from cbs.clipboard.qt_adapter import QtClipboardAdapter
from cbs.config.settings import load_settings
from cbs.gui.main_window import MainWindow
from cbs.logging_setup import configure_logging


def main() -> int:
    config_path = platform.get_config_dir() / "config.json"
    settings = load_settings(config_path)
    logger = configure_logging(settings.log_level, platform.get_log_dir())
    logger.info("Starting Shared Clipboard Service GUI (client_id=%s)", settings.client_id)

    app = QApplication(sys.argv)
    clipboard = QtClipboardAdapter()
    window = MainWindow(settings, config_path, clipboard)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
