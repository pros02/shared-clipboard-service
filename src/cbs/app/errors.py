"""Errors raised by the application/service orchestration layer.

These represent expected, user-facing conditions rather than bugs — the
GUI layer is expected to catch `SendRejectedError` and show `str(error)`
to the user (CLAUDE.md: "add ... meaningful error handling").
"""
from __future__ import annotations

from cbs.domain import ItemType


class SendRejectedError(Exception):
    """Base class for expected, user-facing reasons a send was refused."""


class EmptyClipboardError(SendRejectedError):
    def __init__(self) -> None:
        super().__init__("クリップボードに送信できる内容がありません。")


class UnsupportedClipboardContentError(SendRejectedError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class MultipleFilesNotSupportedError(SendRejectedError):
    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__(
            f"複数ファイル({count}件)は初期バージョンでは送信できません。1つずつ送信してください。"
        )


class SizeLimitExceededError(SendRejectedError):
    def __init__(self, item_type: ItemType, size_bytes: int, limit_bytes: int) -> None:
        self.item_type = item_type
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"{item_type.value}のサイズが上限を超えています "
            f"({size_bytes:,} bytes > {limit_bytes:,} bytes)。"
        )
