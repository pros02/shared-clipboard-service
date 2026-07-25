"""NAS (SMB shared folder) storage backend.

Implements the layout and write protocol decided in
docs/design/requirements_review_v0.1.md, sections 2 and 3.2-3.3:

    SharedClipboard/
        current/current.json
        objects/
        history/
        temp/
        logs/          (reserved for future use; never written to here)

Write protocol: object data is staged under temp/ and atomically moved
into objects/, then a history/<item_id>.json record is written, then
current/current.json is atomically replaced to point at the new item.
Retention (max item count / max total bytes, always keeping the newest
item) is enforced after every write. Stale temp/ files are purged on
startup.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cbs.storage.base import StorageBackend
from cbs.storage.models import SCHEMA_VERSION, ClipboardItemMetadata, ItemType, NewClipboardItem
from cbs.util.atomic_io import atomic_write_text, stage_then_move

logger = logging.getLogger(__name__)

_DEFAULT_EXTENSION = ".bin"
_MAX_SAFE_SUFFIX_LEN = 11
_STALE_TEMP_MAX_AGE = timedelta(hours=24)
_DEFAULT_MAX_RETAINED_ITEMS = 50
_DEFAULT_MAX_RETAINED_TOTAL_BYTES = 2 * 1024**3  # 2 GB


def _is_safe_suffix(suffix: str) -> bool:
    return 1 < len(suffix) <= _MAX_SAFE_SUFFIX_LEN and suffix[1:].isalnum()


def _safe_extension(item: NewClipboardItem) -> str:
    if item.type is ItemType.TEXT:
        return ".txt"
    if item.type is ItemType.IMAGE:
        guessed = f".{item.mime_type.split('/')[-1]}" if "/" in item.mime_type else ""
        return guessed.lower() if _is_safe_suffix(guessed) else _DEFAULT_EXTENSION
    suffix = Path(item.original_name).suffix
    return suffix.lower() if _is_safe_suffix(suffix) else _DEFAULT_EXTENSION


class NasStorageBackend(StorageBackend):
    def __init__(
        self,
        root: Path,
        *,
        max_retained_items: int = _DEFAULT_MAX_RETAINED_ITEMS,
        max_retained_total_bytes: int = _DEFAULT_MAX_RETAINED_TOTAL_BYTES,
    ) -> None:
        self._root = root
        self._max_retained_items = max_retained_items
        self._max_retained_total_bytes = max_retained_total_bytes

    @property
    def _current_dir(self) -> Path:
        return self._root / "current"

    @property
    def _objects_dir(self) -> Path:
        return self._root / "objects"

    @property
    def _history_dir(self) -> Path:
        return self._root / "history"

    @property
    def _temp_dir(self) -> Path:
        return self._root / "temp"

    @property
    def _logs_dir(self) -> Path:
        return self._root / "logs"

    @property
    def _current_json_path(self) -> Path:
        return self._current_dir / "current.json"

    def prepare_for_startup(self) -> None:
        for directory in (
            self._current_dir,
            self._objects_dir,
            self._history_dir,
            self._temp_dir,
            self._logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        self._purge_stale_temp_files()

    def write_item(self, item: NewClipboardItem) -> ClipboardItemMetadata:
        item_id = uuid.uuid4().hex
        created_at_utc = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        sha256 = hashlib.sha256(item.data).hexdigest()
        object_path = f"objects/{item_id}{_safe_extension(item)}"

        stage_then_move(self._temp_dir, self._root / object_path, item.data, stem=item_id)

        metadata = ClipboardItemMetadata(
            schema_version=SCHEMA_VERSION,
            item_id=item_id,
            client_id=item.client_id,
            client_name=item.client_name,
            created_at_utc=created_at_utc,
            type=item.type,
            mime_type=item.mime_type,
            object_path=object_path,
            original_name=item.original_name,
            size_bytes=len(item.data),
            sha256=sha256,
            text_encoding=item.text_encoding,
        )

        self._write_history_entry(metadata)
        self._replace_current(metadata)
        self._enforce_retention()
        return metadata

    def read_current(self) -> ClipboardItemMetadata | None:
        path = self._current_json_path
        if not path.exists():
            return None
        try:
            return self._read_metadata_file(path)
        except (OSError, ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
            logger.warning("Failed to read current item from %s: %s", path, exc)
            return None

    def read_object(self, item: ClipboardItemMetadata) -> bytes:
        path = self._root / item.object_path
        try:
            return path.read_bytes()
        except FileNotFoundError:
            raise FileNotFoundError(f"Object for item {item.item_id!r} not found at {path}") from None

    def list_history(self, limit: int | None = None) -> list[ClipboardItemMetadata]:
        entries: list[ClipboardItemMetadata] = []
        for path in self._history_dir.glob("*.json"):
            try:
                entries.append(self._read_metadata_file(path))
            except (OSError, ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
                logger.warning("Skipping unreadable history entry %s: %s", path, exc)
        entries.sort(key=lambda entry: entry.created_at_utc, reverse=True)
        return entries[:limit] if limit is not None else entries

    def _read_metadata_file(self, path: Path) -> ClipboardItemMetadata:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError(f"{path} does not contain a JSON object")
        return ClipboardItemMetadata.from_dict(raw)

    def _write_history_entry(self, metadata: ClipboardItemMetadata) -> None:
        path = self._history_dir / f"{metadata.item_id}.json"
        atomic_write_text(path, _to_json(metadata))

    def _replace_current(self, metadata: ClipboardItemMetadata) -> None:
        atomic_write_text(self._current_json_path, _to_json(metadata))

    def _purge_stale_temp_files(self) -> None:
        if not self._temp_dir.exists():
            return
        cutoff = datetime.now(UTC).timestamp() - _STALE_TEMP_MAX_AGE.total_seconds()
        for path in self._temp_dir.iterdir():
            if not path.is_file():
                continue
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    logger.info("Removed stale temp file %s", path)
            except OSError as exc:
                logger.warning("Failed to inspect/remove temp file %s: %s", path, exc)

    def _enforce_retention(self) -> None:
        entries = self.list_history()  # newest first
        if len(entries) <= 1:
            return
        total_bytes = sum(entry.size_bytes for entry in entries)
        while len(entries) > 1 and (
            len(entries) > self._max_retained_items or total_bytes > self._max_retained_total_bytes
        ):
            oldest = entries.pop()
            total_bytes -= oldest.size_bytes
            self._delete_item(oldest)

    def _delete_item(self, item: ClipboardItemMetadata) -> None:
        for path in (self._root / item.object_path, self._history_dir / f"{item.item_id}.json"):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Failed to delete %s during retention cleanup: %s", path, exc)
        logger.info("Retention cleanup removed item %s", item.item_id)


def _to_json(metadata: ClipboardItemMetadata) -> str:
    return json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)
