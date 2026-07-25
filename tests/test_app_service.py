from __future__ import annotations

from pathlib import Path

import pytest

from cbs.app.errors import (
    EmptyClipboardError,
    MultipleFilesNotSupportedError,
    SizeLimitExceededError,
    UnsupportedClipboardContentError,
)
from cbs.app.limits import FILE_MAX_BYTES, IMAGE_MAX_BYTES, TEXT_MAX_BYTES
from cbs.app.models import ReceiveStatus
from cbs.app.service import ClipboardService, _check_size
from cbs.clipboard.base import ClipboardAdapter
from cbs.clipboard.models import ClipboardContent
from cbs.domain import ItemType
from cbs.storage.nas_backend import NasStorageBackend
from tests.fakes import FakeClipboardAdapter


def _make_service(
    tmp_path: Path,
    *,
    client_id: str = "client-a",
    client_name: str = "Ryzen7",
    clipboard: ClipboardAdapter | None = None,
) -> tuple[ClipboardService, NasStorageBackend, FakeClipboardAdapter]:
    storage = NasStorageBackend(tmp_path / "nas")
    storage.prepare_for_startup()
    adapter = clipboard if isinstance(clipboard, FakeClipboardAdapter) else FakeClipboardAdapter()
    service = ClipboardService(
        storage,
        adapter,
        client_id=client_id,
        client_name=client_name,
        received_files_dir=tmp_path / "received",
    )
    return service, storage, adapter


# --- send() ---------------------------------------------------------------


def test_send_text_normalizes_crlf_to_lf(tmp_path: Path) -> None:
    service, storage, adapter = _make_service(tmp_path)
    adapter.content = ClipboardContent.from_text("line1\r\nline2\rline3")

    metadata = service.send()

    assert metadata.type is ItemType.TEXT
    assert metadata.text_encoding == "utf-8"
    assert storage.read_object(metadata) == b"line1\nline2\nline3"


def test_send_image_uses_png_mime_type(tmp_path: Path) -> None:
    service, storage, adapter = _make_service(tmp_path)
    adapter.content = ClipboardContent.from_image_png(b"\x89PNG\r\n fake")

    metadata = service.send()

    assert metadata.type is ItemType.IMAGE
    assert metadata.mime_type == "image/png"
    assert storage.read_object(metadata) == b"\x89PNG\r\n fake"


def test_send_single_file_uses_original_name_and_guessed_mime(tmp_path: Path) -> None:
    service, storage, adapter = _make_service(tmp_path)
    file_path = tmp_path / "report.pdf"
    file_path.write_bytes(b"%PDF-1.4 fake")
    adapter.content = ClipboardContent.from_files([file_path])

    metadata = service.send()

    assert metadata.type is ItemType.FILE
    assert metadata.original_name == "report.pdf"
    assert metadata.mime_type == "application/pdf"
    assert storage.read_object(metadata) == b"%PDF-1.4 fake"


def test_send_empty_clipboard_raises(tmp_path: Path) -> None:
    service, _, adapter = _make_service(tmp_path)
    adapter.content = None

    with pytest.raises(EmptyClipboardError):
        service.send()


def test_send_multiple_files_raises(tmp_path: Path) -> None:
    service, _, adapter = _make_service(tmp_path)
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    adapter.content = ClipboardContent.from_files([a, b])

    with pytest.raises(MultipleFilesNotSupportedError):
        service.send()


def test_send_directory_raises(tmp_path: Path) -> None:
    service, _, adapter = _make_service(tmp_path)
    directory = tmp_path / "a_dir"
    directory.mkdir()
    adapter.content = ClipboardContent.from_files([directory])

    with pytest.raises(UnsupportedClipboardContentError):
        service.send()


def test_send_oversized_text_raises(tmp_path: Path) -> None:
    service, _, adapter = _make_service(tmp_path)
    adapter.content = ClipboardContent.from_text("a" * (TEXT_MAX_BYTES + 1))

    with pytest.raises(SizeLimitExceededError):
        service.send()


def test_send_oversized_image_raises(tmp_path: Path) -> None:
    service, _, adapter = _make_service(tmp_path)
    adapter.content = ClipboardContent.from_image_png(b"\x00" * (IMAGE_MAX_BYTES + 1))

    with pytest.raises(SizeLimitExceededError):
        service.send()


def test_check_size_rejects_oversized_file_without_needing_a_real_file() -> None:
    with pytest.raises(SizeLimitExceededError):
        _check_size(ItemType.FILE, FILE_MAX_BYTES + 1)


# --- receive() --------------------------------------------------------------


def test_receive_nothing_available(tmp_path: Path) -> None:
    service, _, adapter = _make_service(tmp_path)

    result = service.receive()

    assert result.status is ReceiveStatus.NOTHING_AVAILABLE
    assert adapter.written == []


def test_receive_ignores_own_client_item(tmp_path: Path) -> None:
    storage = NasStorageBackend(tmp_path / "nas")
    storage.prepare_for_startup()
    sender_adapter = FakeClipboardAdapter(ClipboardContent.from_text("mine"))
    sender = ClipboardService(
        storage,
        sender_adapter,
        client_id="client-a",
        client_name="Ryzen7",
        received_files_dir=tmp_path / "received",
    )
    sender.send()

    receiver_adapter = FakeClipboardAdapter()
    receiver = ClipboardService(
        storage,
        receiver_adapter,
        client_id="client-a",
        client_name="Ryzen7",
        received_files_dir=tmp_path / "received",
    )

    result = receiver.receive()

    assert result.status is ReceiveStatus.IGNORED_OWN_CLIENT
    assert receiver_adapter.written == []


def test_receive_text_from_other_client(tmp_path: Path) -> None:
    storage = NasStorageBackend(tmp_path / "nas")
    storage.prepare_for_startup()
    sender = ClipboardService(
        storage,
        FakeClipboardAdapter(ClipboardContent.from_text("hello from client A")),
        client_id="client-a",
        client_name="Ryzen7",
        received_files_dir=tmp_path / "received-a",
    )
    sender.send()

    receiver_adapter = FakeClipboardAdapter()
    receiver = ClipboardService(
        storage,
        receiver_adapter,
        client_id="client-b",
        client_name="Ryzen3",
        received_files_dir=tmp_path / "received-b",
    )

    result = receiver.receive()

    assert result.status is ReceiveStatus.RECEIVED
    assert receiver_adapter.content is not None
    assert receiver_adapter.content.text == "hello from client A"


def test_receive_file_from_other_client_stages_with_original_name(tmp_path: Path) -> None:
    storage = NasStorageBackend(tmp_path / "nas")
    storage.prepare_for_startup()
    source_file = tmp_path / "report.pdf"
    source_file.write_bytes(b"%PDF-1.4 fake")
    sender = ClipboardService(
        storage,
        FakeClipboardAdapter(ClipboardContent.from_files([source_file])),
        client_id="client-a",
        client_name="Ryzen7",
        received_files_dir=tmp_path / "received-a",
    )
    sender.send()

    received_dir = tmp_path / "received-b"
    receiver_adapter = FakeClipboardAdapter()
    receiver = ClipboardService(
        storage,
        receiver_adapter,
        client_id="client-b",
        client_name="Ryzen3",
        received_files_dir=received_dir,
    )

    result = receiver.receive()

    assert result.status is ReceiveStatus.RECEIVED
    assert receiver_adapter.content is not None
    staged_paths = receiver_adapter.content.file_paths
    assert len(staged_paths) == 1
    assert staged_paths[0] == received_dir / "report.pdf"
    assert staged_paths[0].read_bytes() == b"%PDF-1.4 fake"


def test_receive_file_sanitizes_unsafe_original_name(tmp_path: Path) -> None:
    storage = NasStorageBackend(tmp_path / "nas")
    storage.prepare_for_startup()
    source_file = tmp_path / "evil.txt"
    source_file.write_bytes(b"payload")
    sender = ClipboardService(
        storage,
        FakeClipboardAdapter(ClipboardContent.from_files([source_file])),
        client_id="client-a",
        client_name="Ryzen7",
        received_files_dir=tmp_path / "received-a",
    )
    metadata = sender.send()

    # Simulate a malicious/odd original_name arriving via the NAS metadata.
    tampered = storage.list_history()[0]
    object_bytes = storage.read_object(tampered)
    from dataclasses import replace

    tampered = replace(tampered, original_name="../../../etc/passwd")

    received_dir = tmp_path / "received-b"
    receiver_adapter = FakeClipboardAdapter()
    receiver = ClipboardService(
        storage,
        receiver_adapter,
        client_id="client-b",
        client_name="Ryzen3",
        received_files_dir=received_dir,
    )
    content = receiver._content_from_metadata(tampered, object_bytes)  # type: ignore[attr-defined]

    assert content.file_paths[0].parent == received_dir
    assert content.file_paths[0].name == "passwd"
    assert metadata.original_name == "evil.txt"
