"""Clipboard adapter abstraction.

Keeps clipboard access behind a swappable, mockable interface so the
application layer never talks to a specific OS/toolkit clipboard API
directly (CLAUDE.md: "keep clipboard platform adapters mockable").
"""
from __future__ import annotations

import abc

from cbs.clipboard.models import ClipboardContent


class ClipboardAdapter(abc.ABC):
    @abc.abstractmethod
    def read(self) -> ClipboardContent | None:
        """Return the current local clipboard content, or None if empty/unsupported."""

    @abc.abstractmethod
    def write(self, content: ClipboardContent) -> None:
        """Set the local clipboard to the given content."""
