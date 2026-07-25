"""Storage backend abstraction.

Lets the NAS-backed implementation (Phase 1) be swapped for a future
SQLite or REST API backend without touching the application layer, per
the CLAUDE.md architecture rule "abstract the storage backend".
"""
from __future__ import annotations

import abc

from cbs.storage.models import ClipboardItemMetadata, NewClipboardItem


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def prepare_for_startup(self) -> None:
        """Ensure the storage layout exists and clear stale temp files."""

    @abc.abstractmethod
    def write_item(self, item: NewClipboardItem) -> ClipboardItemMetadata:
        """Persist a new clipboard item and make it the current item."""

    @abc.abstractmethod
    def read_current(self) -> ClipboardItemMetadata | None:
        """Return the current item's metadata, or None if unset/unreadable."""

    @abc.abstractmethod
    def read_object(self, item: ClipboardItemMetadata) -> bytes:
        """Return the raw bytes stored for an item."""

    @abc.abstractmethod
    def list_history(self, limit: int | None = None) -> list[ClipboardItemMetadata]:
        """Return history entries, newest first."""
