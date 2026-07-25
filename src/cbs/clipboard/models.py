"""Data model for content read from or written to the local OS clipboard.

Distinct from cbs.storage.models.ClipboardItemMetadata: this represents
live clipboard content on this machine, before it has been hashed, named,
or persisted to the NAS.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from cbs.domain import ItemType


@dataclass(frozen=True)
class ClipboardContent:
    type: ItemType
    text: str | None = None
    image_png: bytes | None = None
    file_paths: tuple[Path, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.type is ItemType.TEXT and self.text is None:
            raise ValueError("ClipboardContent(type=TEXT) requires text")
        if self.type is ItemType.IMAGE and self.image_png is None:
            raise ValueError("ClipboardContent(type=IMAGE) requires image_png")
        if self.type is ItemType.FILE and not self.file_paths:
            raise ValueError("ClipboardContent(type=FILE) requires at least one file path")

    @staticmethod
    def from_text(text: str) -> ClipboardContent:
        return ClipboardContent(type=ItemType.TEXT, text=text)

    @staticmethod
    def from_image_png(data: bytes) -> ClipboardContent:
        return ClipboardContent(type=ItemType.IMAGE, image_png=data)

    @staticmethod
    def from_files(paths: Sequence[Path]) -> ClipboardContent:
        return ClipboardContent(type=ItemType.FILE, file_paths=tuple(paths))
