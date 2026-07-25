"""Data model for clipboard items stored in the shared NAS folder.

Mirrors the schema decided in docs/design/requirements_review_v0.1.md,
section 3.3. The same structure is used for both current/current.json and
each history/<item_id>.json record.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

SCHEMA_VERSION = 1


class ItemType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


@dataclass(frozen=True)
class ClipboardItemMetadata:
    schema_version: int
    item_id: str
    client_id: str
    client_name: str
    created_at_utc: str
    type: ItemType
    mime_type: str
    object_path: str
    original_name: str
    size_bytes: int
    sha256: str
    text_encoding: str | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClipboardItemMetadata:
        text_encoding = data.get("text_encoding")
        return cls(
            schema_version=int(data["schema_version"]),
            item_id=str(data["item_id"]),
            client_id=str(data["client_id"]),
            client_name=str(data["client_name"]),
            created_at_utc=str(data["created_at_utc"]),
            type=ItemType(data["type"]),
            mime_type=str(data["mime_type"]),
            object_path=str(data["object_path"]),
            original_name=str(data["original_name"]),
            size_bytes=int(data["size_bytes"]),
            sha256=str(data["sha256"]),
            text_encoding=str(text_encoding) if text_encoding is not None else None,
        )


@dataclass(frozen=True)
class NewClipboardItem:
    """Input for StorageBackend.write_item — everything the caller supplies.

    Fields the storage backend computes itself (item_id, created_at_utc,
    object_path, size_bytes, sha256) are not part of this input.
    """

    data: bytes
    type: ItemType
    mime_type: str
    original_name: str
    client_id: str
    client_name: str
    text_encoding: str | None = None
