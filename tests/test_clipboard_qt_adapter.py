"""Integration tests for QtClipboardAdapter against the real local clipboard.

Unlike the model tests, these exercise actual OS clipboard I/O through
PySide6 and are skipped if a Qt GUI application cannot be created (e.g. no
display available, such as a headless Linux CI runner). Note: running
these tests overwrites the local clipboard's current contents.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

from cbs.clipboard.models import ClipboardContent


def _make_one_pixel_png() -> bytes:
    """Build a minimal valid 1x1 RGB PNG without depending on an image library."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8-bit depth, RGB
    idat = zlib.compress(b"\x00\xff\x00\x00")  # filter byte + one red pixel
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


_ONE_PIXEL_PNG = _make_one_pixel_png()


@pytest.fixture(scope="module")
def adapter():  # type: ignore[no-untyped-def]
    try:
        from cbs.clipboard.qt_adapter import QtClipboardAdapter

        return QtClipboardAdapter()
    except Exception as exc:  # noqa: BLE001 - probing environment/display availability
        pytest.skip(f"Qt clipboard unavailable in this environment: {exc}")


def test_write_then_read_text_round_trips(adapter) -> None:  # type: ignore[no-untyped-def]
    adapter.write(ClipboardContent.from_text("hello from cbs phase 2"))

    result = adapter.read()

    assert result is not None
    assert result.text == "hello from cbs phase 2"


def test_write_then_read_image_round_trips(adapter) -> None:  # type: ignore[no-untyped-def]
    adapter.write(ClipboardContent.from_image_png(_ONE_PIXEL_PNG))

    result = adapter.read()

    assert result is not None
    assert result.image_png is not None
    assert result.image_png.startswith(b"\x89PNG")


def test_write_then_read_files_round_trips(adapter, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    file_path = tmp_path / "sample.txt"
    file_path.write_text("data", encoding="utf-8")

    adapter.write(ClipboardContent.from_files([file_path]))

    result = adapter.read()

    assert result is not None
    resolved = {p.resolve() for p in result.file_paths}
    assert file_path.resolve() in resolved
