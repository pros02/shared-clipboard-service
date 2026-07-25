"""Qt-based clipboard adapter (PySide6), used for both Windows and Ubuntu.

Qt's QClipboard talks to the native OS clipboard through Qt's platform
plugin (Win32 on Windows; X11 or Wayland on Ubuntu), so a single
implementation covers both target platforms without OS-specific code
here. Initial scope is limited to plain text, PNG images, and local file
references (see docs/design/requirements_review_v0.1.md).

Wayland ties clipboard access to a real, focusable surface rather than
allowing a fully windowless client to read/write the selection (unlike
X11, which is more permissive here). A windowless QGuiApplication was
confirmed unable to read clipboard content set by other apps on Ubuntu
26.04/GNOME/Wayland. To work around this, a tiny off-screen window is
kept alive for the process lifetime, and the Qt event loop is pumped
around clipboard access so Wayland's asynchronous data-offer protocol
has a chance to complete.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PySide6.QtCore import QEventLoop, QMimeData, QUrl
from PySide6.QtGui import QClipboard, QGuiApplication, QImage
from PySide6.QtWidgets import QApplication, QWidget

from cbs.clipboard.base import ClipboardAdapter
from cbs.clipboard.models import ClipboardContent
from cbs.domain import ItemType

logger = logging.getLogger(__name__)

_EVENT_PUMP_MAX_MS = 200

_hidden_window: QWidget | None = None


def _pump_events(max_time_ms: int = _EVENT_PUMP_MAX_MS) -> None:
    app = QGuiApplication.instance()
    if app is not None:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, max_time_ms)


def _ensure_application() -> None:
    global _hidden_window
    if QApplication.instance() is None:
        QApplication([])
    if _hidden_window is None:
        _hidden_window = QWidget()
        _hidden_window.setGeometry(-10000, -10000, 1, 1)
        _hidden_window.show()
        _pump_events()


def _image_to_png_bytes(image: QImage) -> bytes:
    # Saving through a real .png-suffixed file lets Qt infer the format from
    # the extension; this proved more reliable than QImage.save() into a
    # QBuffer with an explicit format argument (PySide6 overload quirk).
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "clipboard_image.png"
        if not image.save(str(path)):
            raise RuntimeError("Failed to encode clipboard image as PNG")
        return path.read_bytes()


class QtClipboardAdapter(ClipboardAdapter):
    def __init__(self) -> None:
        _ensure_application()

    def _clipboard(self) -> QClipboard:
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            raise RuntimeError("No system clipboard is available on this platform")
        return clipboard

    def read(self) -> ClipboardContent | None:
        clipboard = self._clipboard()
        _pump_events()
        mime = clipboard.mimeData()
        if mime is None:
            return None

        if mime.hasUrls():
            paths = [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]
            if paths:
                return ClipboardContent.from_files(paths)

        if mime.hasImage():
            image = clipboard.image()
            if not image.isNull():
                return ClipboardContent.from_image_png(_image_to_png_bytes(image))

        if mime.hasText():
            text = clipboard.text()
            if text:
                return ClipboardContent.from_text(text)

        return None

    def write(self, content: ClipboardContent) -> None:
        clipboard = self._clipboard()

        if content.type is ItemType.TEXT:
            assert content.text is not None
            clipboard.setText(content.text)
        elif content.type is ItemType.IMAGE:
            assert content.image_png is not None
            image = QImage()
            if not image.loadFromData(content.image_png):
                raise ValueError("Could not decode image_png as PNG data")
            clipboard.setImage(image)
        elif content.type is ItemType.FILE:
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(path)) for path in content.file_paths])
            clipboard.setMimeData(mime)

        _pump_events()
