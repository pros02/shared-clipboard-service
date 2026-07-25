from __future__ import annotations

from pathlib import Path

import pytest

from cbs.clipboard.models import ClipboardContent
from cbs.domain import ItemType


def test_from_text_sets_type_and_text() -> None:
    content = ClipboardContent.from_text("hello")

    assert content.type is ItemType.TEXT
    assert content.text == "hello"


def test_from_image_png_sets_type_and_bytes() -> None:
    content = ClipboardContent.from_image_png(b"\x89PNG\r\n")

    assert content.type is ItemType.IMAGE
    assert content.image_png == b"\x89PNG\r\n"


def test_from_files_sets_type_and_paths() -> None:
    paths = [Path("a.txt"), Path("b.txt")]

    content = ClipboardContent.from_files(paths)

    assert content.type is ItemType.FILE
    assert content.file_paths == tuple(paths)


def test_text_type_requires_text() -> None:
    with pytest.raises(ValueError, match="requires text"):
        ClipboardContent(type=ItemType.TEXT, text=None)


def test_image_type_requires_image_bytes() -> None:
    with pytest.raises(ValueError, match="requires image_png"):
        ClipboardContent(type=ItemType.IMAGE, image_png=None)


def test_file_type_requires_at_least_one_path() -> None:
    with pytest.raises(ValueError, match="requires at least one file path"):
        ClipboardContent(type=ItemType.FILE, file_paths=())
