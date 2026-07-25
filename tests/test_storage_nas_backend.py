from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from cbs.storage.models import ItemType, NewClipboardItem
from cbs.storage.nas_backend import NasStorageBackend

_SORT_DELAY_SECONDS = 0.01


def _make_item(
    data: bytes = b"hello",
    *,
    type_: ItemType = ItemType.TEXT,
    mime_type: str = "text/plain",
    original_name: str = "note.txt",
    client_id: str = "client-1",
    client_name: str = "Ryzen7",
) -> NewClipboardItem:
    return NewClipboardItem(
        data=data,
        type=type_,
        mime_type=mime_type,
        original_name=original_name,
        client_id=client_id,
        client_name=client_name,
        text_encoding="utf-8" if type_ is ItemType.TEXT else None,
    )


def test_prepare_for_startup_creates_all_directories(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)

    backend.prepare_for_startup()

    for name in ("current", "objects", "history", "temp", "logs"):
        assert (tmp_path / name).is_dir()


def test_write_item_creates_object_history_and_current(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()

    metadata = backend.write_item(_make_item(b"hello world"))

    object_file = tmp_path / metadata.object_path
    history_file = tmp_path / "history" / f"{metadata.item_id}.json"
    current_file = tmp_path / "current" / "current.json"

    assert object_file.read_bytes() == b"hello world"
    assert history_file.exists()
    assert current_file.exists()
    assert metadata.size_bytes == len(b"hello world")
    assert metadata.object_path.endswith(".txt")
    assert len(metadata.sha256) == 64


def test_read_current_reflects_latest_write(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()

    backend.write_item(_make_item(b"first"))
    second = backend.write_item(_make_item(b"second"))

    current = backend.read_current()

    assert current is not None
    assert current.item_id == second.item_id


def test_read_current_returns_none_when_missing(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()

    assert backend.read_current() is None


def test_read_current_returns_none_on_corrupt_json(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()
    (tmp_path / "current" / "current.json").write_text("{not valid", encoding="utf-8")

    assert backend.read_current() is None


def test_read_current_returns_none_for_valid_json_missing_required_field(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()
    # Valid JSON, but missing "sha256" — a different failure mode than
    # outright corrupt JSON (e.g. a future schema change, hand-edited file).
    (tmp_path / "current" / "current.json").write_text(
        '{"schema_version": 1, "item_id": "x", "client_id": "c", "client_name": "n", '
        '"created_at_utc": "t", "type": "text", "mime_type": "text/plain", '
        '"object_path": "objects/x.txt", "original_name": "x.txt", "size_bytes": 1}',
        encoding="utf-8",
    )

    assert backend.read_current() is None


def test_list_history_skips_entry_with_invalid_type_value(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()
    good = backend.write_item(_make_item(b"good"))
    (tmp_path / "history" / "bogus.json").write_text(
        '{"schema_version": 1, "item_id": "y", "client_id": "c", "client_name": "n", '
        '"created_at_utc": "t", "type": "not-a-real-type", "mime_type": "text/plain", '
        '"object_path": "objects/y.txt", "original_name": "y.txt", "size_bytes": 1, '
        '"sha256": "deadbeef", "text_encoding": null}',
        encoding="utf-8",
    )

    history = backend.list_history()

    assert [entry.item_id for entry in history] == [good.item_id]


def test_write_item_failure_before_current_update_leaves_previous_current_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate a crash between writing the history entry and updating
    current.json (e.g. process killed, NAS disconnects mid-operation).
    The object and history entry for the failed item may be orphaned, but
    the previously-current item must stay intact and readable — no partial
    or corrupted current.json."""
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()
    first = backend.write_item(_make_item(b"first"))

    original_replace_current = backend._replace_current

    def _boom(metadata: object) -> None:
        raise OSError("simulated NAS disconnect mid-write")

    monkeypatch.setattr(backend, "_replace_current", _boom)
    with pytest.raises(OSError):
        backend.write_item(_make_item(b"second"))

    monkeypatch.setattr(backend, "_replace_current", original_replace_current)
    current = backend.read_current()
    assert current is not None
    assert current.item_id == first.item_id
    assert backend.read_object(current) == b"first"


def test_list_history_sorted_newest_first_and_respects_limit(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()

    for i in range(5):
        backend.write_item(_make_item(f"item-{i}".encode()))
        time.sleep(_SORT_DELAY_SECONDS)

    history = backend.list_history(limit=3)

    assert len(history) == 3
    timestamps = [entry.created_at_utc for entry in history]
    assert timestamps == sorted(timestamps, reverse=True)


def test_list_history_skips_corrupt_entry(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()

    good = backend.write_item(_make_item(b"good"))
    (tmp_path / "history" / "corrupt.json").write_text("{not valid", encoding="utf-8")

    history = backend.list_history()

    assert [entry.item_id for entry in history] == [good.item_id]


def test_read_object_returns_bytes(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()

    metadata = backend.write_item(_make_item(b"payload"))

    assert backend.read_object(metadata) == b"payload"


def test_read_object_raises_when_object_missing(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()

    metadata = backend.write_item(_make_item(b"payload"))
    (tmp_path / metadata.object_path).unlink()

    with pytest.raises(FileNotFoundError):
        backend.read_object(metadata)


def test_retention_by_item_count_keeps_only_newest(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path, max_retained_items=3, max_retained_total_bytes=10**9)
    backend.prepare_for_startup()

    written = []
    for i in range(5):
        written.append(backend.write_item(_make_item(f"item-{i}".encode())))
        time.sleep(_SORT_DELAY_SECONDS)

    remaining = {entry.item_id for entry in backend.list_history()}

    assert remaining == {item.item_id for item in written[-3:]}
    for item in written[:-3]:
        assert not (tmp_path / item.object_path).exists()
        assert not (tmp_path / "history" / f"{item.item_id}.json").exists()


def test_retention_by_total_size_keeps_only_newest(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path, max_retained_items=100, max_retained_total_bytes=15)
    backend.prepare_for_startup()

    written = []
    for _ in range(5):
        written.append(backend.write_item(_make_item(b"12345")))  # 5 bytes each
        time.sleep(_SORT_DELAY_SECONDS)

    remaining = {entry.item_id for entry in backend.list_history()}

    assert remaining == {item.item_id for item in written[-3:]}


def test_retention_always_keeps_at_least_the_newest_item(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path, max_retained_items=1, max_retained_total_bytes=1)
    backend.prepare_for_startup()

    metadata = backend.write_item(_make_item(b"this is definitely over one byte"))

    history = backend.list_history()
    assert len(history) == 1
    assert history[0].item_id == metadata.item_id


def test_purge_stale_temp_files_removes_old_but_keeps_recent(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()

    old_file = tmp_path / "temp" / "old.tmp"
    old_file.write_bytes(b"stale")
    old_timestamp = time.time() - (25 * 3600)
    os.utime(old_file, (old_timestamp, old_timestamp))

    fresh_file = tmp_path / "temp" / "fresh.tmp"
    fresh_file.write_bytes(b"fresh")

    backend.prepare_for_startup()

    assert not old_file.exists()
    assert fresh_file.exists()


def test_object_extension_by_type(tmp_path: Path) -> None:
    backend = NasStorageBackend(tmp_path)
    backend.prepare_for_startup()

    text_item = backend.write_item(_make_item(b"hi", type_=ItemType.TEXT))
    image_item = backend.write_item(
        _make_item(b"\x89PNG", type_=ItemType.IMAGE, mime_type="image/png", original_name="clip.png")
    )
    file_item = backend.write_item(
        _make_item(b"zipdata", type_=ItemType.FILE, mime_type="application/zip", original_name="archive.zip")
    )
    weird_file_item = backend.write_item(
        _make_item(b"data", type_=ItemType.FILE, mime_type="application/octet-stream", original_name="no_extension")
    )

    assert text_item.object_path.endswith(".txt")
    assert image_item.object_path.endswith(".png")
    assert file_item.object_path.endswith(".zip")
    assert weird_file_item.object_path.endswith(".bin")
