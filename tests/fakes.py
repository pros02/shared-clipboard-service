"""Shared test doubles."""
from __future__ import annotations

from cbs.clipboard.base import ClipboardAdapter
from cbs.clipboard.models import ClipboardContent


class FakeClipboardAdapter(ClipboardAdapter):
    def __init__(self, initial: ClipboardContent | None = None) -> None:
        self.content = initial
        self.written: list[ClipboardContent] = []

    def read(self) -> ClipboardContent | None:
        return self.content

    def write(self, content: ClipboardContent) -> None:
        self.written.append(content)
        self.content = content
