"""GUI-based clipboard smoke test.

Unlike clipboard_smoke_test.py (a terminal script whose window, if any,
never gets real focus), this shows an actual visible window with a
button. Clicking the button gives this window real focus at the moment
of the read — matching how the real app's "send" button will behave.
This matters on Wayland/GNOME, where clipboard content can be gated by
window focus and the xdg-desktop-portal.

Run on the target machine's desktop session:

    python scripts/clipboard_smoke_test_gui.py

Workflow: copy something in another app, click this window to focus
it, then click "Read Clipboard".
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from cbs.clipboard.models import ClipboardContent
from cbs.clipboard.qt_adapter import QtClipboardAdapter
from cbs.domain import ItemType


def _describe(content: ClipboardContent | None) -> str:
    if content is None:
        return "(nothing detected / empty or unsupported clipboard content)"
    if content.type is ItemType.TEXT:
        return f"TEXT: {content.text!r}"
    if content.type is ItemType.IMAGE:
        size = len(content.image_png) if content.image_png else 0
        return f"IMAGE: {size} bytes of PNG data"
    return "FILES: " + ", ".join(str(p) for p in content.file_paths)


class SmokeTestWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CBS Clipboard Smoke Test")
        self.resize(520, 220)

        self._adapter = QtClipboardAdapter()

        instructions = QLabel(
            "1. Copy something (text / image / files) in another app.\n"
            "2. Click this window to focus it.\n"
            "3. Click 'Read Clipboard' below."
        )
        self._result = QLabel("(no read yet)")
        self._result.setWordWrap(True)

        read_button = QPushButton("Read Clipboard")
        read_button.clicked.connect(self._on_read_clicked)

        write_button = QPushButton("Write test text to clipboard")
        write_button.clicked.connect(self._on_write_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(instructions)
        layout.addWidget(read_button)
        layout.addWidget(write_button)
        layout.addWidget(self._result)

    def _on_read_clicked(self) -> None:
        content = self._adapter.read()
        self._result.setText("Detected: " + _describe(content))

    def _on_write_clicked(self) -> None:
        self._adapter.write(ClipboardContent.from_text("shared-clipboard-service smoke test"))
        self._result.setText("Wrote text to the clipboard. Try pasting it in another app.")


def main() -> None:
    app = QApplication(sys.argv)
    window = SmokeTestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
