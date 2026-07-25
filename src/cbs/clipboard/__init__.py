"""Clipboard adapter layer.

`ClipboardAdapter` is the interface the application layer depends on;
`QtClipboardAdapter` is the initial implementation, backed by PySide6's
QClipboard and shared by both Windows and Ubuntu. A future OS-specific
implementation can replace it without changing callers.
"""
from __future__ import annotations

from cbs.clipboard.base import ClipboardAdapter
from cbs.clipboard.models import ClipboardContent
from cbs.clipboard.qt_adapter import QtClipboardAdapter

__all__ = ["ClipboardAdapter", "ClipboardContent", "QtClipboardAdapter"]
