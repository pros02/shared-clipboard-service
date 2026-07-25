"""Application/service orchestration layer.

`ClipboardService` implements send/receive: converting local clipboard
content into a stored item (with size-limit enforcement and text
normalization) and converting a stored item back into local clipboard
content (ignoring items created by this same client).
"""
from __future__ import annotations

from cbs.app.errors import (
    EmptyClipboardError,
    MultipleFilesNotSupportedError,
    SendRejectedError,
    SizeLimitExceededError,
    UnsupportedClipboardContentError,
)
from cbs.app.models import ReceiveResult, ReceiveStatus
from cbs.app.service import ClipboardService

__all__ = [
    "ClipboardService",
    "EmptyClipboardError",
    "MultipleFilesNotSupportedError",
    "ReceiveResult",
    "ReceiveStatus",
    "SendRejectedError",
    "SizeLimitExceededError",
    "UnsupportedClipboardContentError",
]
