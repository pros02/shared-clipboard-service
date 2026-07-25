from __future__ import annotations

from pathlib import Path

from cbs.util.atomic_io import atomic_write_bytes, atomic_write_text


def test_atomic_write_text_creates_file_with_content(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "file.txt"

    atomic_write_text(target, "hello world")

    assert target.read_text(encoding="utf-8") == "hello world"


def test_atomic_write_leaves_no_temp_file_behind(tmp_path: Path) -> None:
    target = tmp_path / "file.bin"

    atomic_write_bytes(target, b"data")

    leftovers = [p for p in tmp_path.iterdir() if p != target]
    assert leftovers == []


def test_atomic_write_overwrites_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    atomic_write_text(target, "old")

    atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "new"
