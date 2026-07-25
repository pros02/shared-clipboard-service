"""Storage abstraction layer.

`StorageBackend` is the interface the application layer depends on;
`NasStorageBackend` is the initial implementation backed by the NAS SMB
share. A future SQLite or REST API backend can implement the same
interface without changing callers (see CLAUDE.md architecture rules).
"""
from __future__ import annotations

from cbs.storage.base import StorageBackend
from cbs.storage.models import ClipboardItemMetadata, ItemType, NewClipboardItem
from cbs.storage.nas_backend import NasStorageBackend

__all__ = [
    "ClipboardItemMetadata",
    "ItemType",
    "NasStorageBackend",
    "NewClipboardItem",
    "StorageBackend",
]
