"""Send/receive orchestration.

Ties the clipboard adapter and storage backend together: converts local
clipboard content into a storage item on send (enforcing size limits and
normalizing text line endings — docs/design/requirements_review_v0.1.md
3.4-3.5), and converts a stored item back into local clipboard content on
receive (ignoring items created by this same client, per CLAUDE.md).

Neither ClipboardService method touches Qt itself beyond the adapter
calls it's given; callers that need to keep a GUI responsive during a
large file's hashing/upload can run write_item()-heavy work on a
background thread as long as clipboard reads/writes stay on the Qt main
thread (QClipboard is not thread-safe).
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from cbs.app.errors import (
    EmptyClipboardError,
    MultipleFilesNotSupportedError,
    SizeLimitExceededError,
    UnsupportedClipboardContentError,
)
from cbs.app.limits import limit_for
from cbs.app.models import ReceiveResult, ReceiveStatus
from cbs.clipboard.base import ClipboardAdapter
from cbs.clipboard.models import ClipboardContent
from cbs.domain import ItemType
from cbs.storage.base import StorageBackend
from cbs.storage.models import ClipboardItemMetadata, NewClipboardItem
from cbs.util.atomic_io import atomic_write_bytes


class ClipboardService:
    def __init__(
        self,
        storage: StorageBackend,
        clipboard: ClipboardAdapter,
        *,
        client_id: str,
        client_name: str,
        received_files_dir: Path,
    ) -> None:
        self._storage = storage
        self._clipboard = clipboard
        self._client_id = client_id
        self._client_name = client_name
        self._received_files_dir = received_files_dir

    @property
    def client_id(self) -> str:
        return self._client_id

    def peek_current(self) -> ClipboardItemMetadata | None:
        """Return the NAS's current item metadata without touching the clipboard.

        Used by AutoReceivePoller to decide whether a new item is worth
        receiving before paying the cost of a clipboard write.
        """
        return self._storage.read_current()

    def list_history(self, limit: int | None = None) -> list[ClipboardItemMetadata]:
        return self._storage.list_history(limit)

    def copy_history_item_to_clipboard(self, metadata: ClipboardItemMetadata) -> None:
        """Re-copy a history entry to the local clipboard, regardless of client_id."""
        content = self.fetch_content_for(metadata)
        self._clipboard.write(content)

    def send(self) -> ClipboardItemMetadata:
        content = self._clipboard.read()
        if content is None:
            raise EmptyClipboardError()
        return self.send_content(content)

    def send_content(self, content: ClipboardContent) -> ClipboardItemMetadata:
        """Validate and persist already-captured clipboard content.

        Does not touch the clipboard itself, so — unlike send() — this is
        safe to run on a background thread (e.g. so hashing/uploading a
        large file doesn't freeze a GUI's main thread).
        """
        new_item = self._build_new_item(content)
        return self._storage.write_item(new_item)

    def receive(self) -> ReceiveResult:
        current = self._storage.read_current()
        if current is None:
            return ReceiveResult(status=ReceiveStatus.NOTHING_AVAILABLE, metadata=None)
        if current.client_id == self._client_id:
            return ReceiveResult(status=ReceiveStatus.IGNORED_OWN_CLIENT, metadata=current)

        content = self.fetch_content_for(current)
        self._clipboard.write(content)
        return ReceiveResult(status=ReceiveStatus.RECEIVED, metadata=current)

    def fetch_content_for(self, metadata: ClipboardItemMetadata) -> ClipboardContent:
        """Read a stored item's bytes and stage them as ClipboardContent.

        Does not touch the clipboard itself, so — unlike receive() — this
        is safe to run on a background thread.
        """
        data = self._storage.read_object(metadata)
        return self._content_from_metadata(metadata, data)

    def _build_new_item(self, content: ClipboardContent) -> NewClipboardItem:
        if content.type is ItemType.TEXT:
            return self._build_text_item(content)
        if content.type is ItemType.IMAGE:
            return self._build_image_item(content)
        return self._build_file_item(content)

    def _build_text_item(self, content: ClipboardContent) -> NewClipboardItem:
        assert content.text is not None
        normalized = content.text.replace("\r\n", "\n").replace("\r", "\n")
        data = normalized.encode("utf-8")
        _check_size(ItemType.TEXT, len(data))
        return NewClipboardItem(
            data=data,
            type=ItemType.TEXT,
            mime_type="text/plain",
            original_name="clipboard.txt",
            client_id=self._client_id,
            client_name=self._client_name,
            text_encoding="utf-8",
        )

    def _build_image_item(self, content: ClipboardContent) -> NewClipboardItem:
        assert content.image_png is not None
        _check_size(ItemType.IMAGE, len(content.image_png))
        return NewClipboardItem(
            data=content.image_png,
            type=ItemType.IMAGE,
            mime_type="image/png",
            original_name="clipboard.png",
            client_id=self._client_id,
            client_name=self._client_name,
        )

    def _build_file_item(self, content: ClipboardContent) -> NewClipboardItem:
        if len(content.file_paths) == 0:
            raise EmptyClipboardError()
        if len(content.file_paths) > 1:
            raise MultipleFilesNotSupportedError(len(content.file_paths))

        path = content.file_paths[0]
        if path.is_dir():
            raise UnsupportedClipboardContentError(f"フォルダの送信は未対応です: {path}")
        try:
            size_bytes = path.stat().st_size
        except OSError as exc:
            raise UnsupportedClipboardContentError(f"ファイルを読み込めません: {path} ({exc})") from exc
        _check_size(ItemType.FILE, size_bytes)

        data = path.read_bytes()
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return NewClipboardItem(
            data=data,
            type=ItemType.FILE,
            mime_type=mime_type,
            original_name=path.name,
            client_id=self._client_id,
            client_name=self._client_name,
        )

    def _content_from_metadata(self, metadata: ClipboardItemMetadata, data: bytes) -> ClipboardContent:
        if metadata.type is ItemType.TEXT:
            return ClipboardContent.from_text(data.decode(metadata.text_encoding or "utf-8"))
        if metadata.type is ItemType.IMAGE:
            return ClipboardContent.from_image_png(data)

        filename = _safe_local_filename(metadata.original_name, fallback=Path(metadata.object_path).name)
        staged_path = self._received_files_dir / filename
        atomic_write_bytes(staged_path, data)
        return ClipboardContent.from_files([staged_path])


def _check_size(item_type: ItemType, size_bytes: int) -> None:
    limit = limit_for(item_type)
    if size_bytes > limit:
        raise SizeLimitExceededError(item_type, size_bytes, limit)


def _safe_local_filename(original_name: str, *, fallback: str) -> str:
    name = Path(original_name).name.strip()
    if not name or name in {".", ".."}:
        return fallback
    return name
