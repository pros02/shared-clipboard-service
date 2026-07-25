from __future__ import annotations

from typing import Any

import pytest

from cbs.storage.models import ClipboardItemMetadata, ItemType


def _sample_dict() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "item_id": "abc123",
        "client_id": "client-1",
        "client_name": "Ryzen7",
        "created_at_utc": "2026-07-25T12:00:00.000Z",
        "type": "text",
        "mime_type": "text/plain",
        "object_path": "objects/abc123.txt",
        "original_name": "note.txt",
        "size_bytes": 5,
        "sha256": "deadbeef",
        "text_encoding": "utf-8",
    }


def test_round_trip_to_dict_from_dict() -> None:
    original = ClipboardItemMetadata.from_dict(_sample_dict())

    restored = ClipboardItemMetadata.from_dict(original.to_dict())

    assert restored == original
    assert restored.type is ItemType.TEXT


def test_to_dict_serializes_type_as_plain_string() -> None:
    metadata = ClipboardItemMetadata.from_dict(_sample_dict())

    assert metadata.to_dict()["type"] == "text"


def test_from_dict_missing_field_raises_key_error() -> None:
    data = _sample_dict()
    del data["sha256"]

    with pytest.raises(KeyError):
        ClipboardItemMetadata.from_dict(data)


def test_from_dict_invalid_type_raises_value_error() -> None:
    data = _sample_dict()
    data["type"] = "not-a-real-type"

    with pytest.raises(ValueError):
        ClipboardItemMetadata.from_dict(data)


def test_text_encoding_none_is_preserved() -> None:
    data = _sample_dict()
    data["text_encoding"] = None

    metadata = ClipboardItemMetadata.from_dict(data)

    assert metadata.text_encoding is None
