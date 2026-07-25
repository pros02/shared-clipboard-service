"""Application/service orchestration layer.

`ClipboardService` implements send/receive: converting local clipboard
content into a stored item (with size-limit enforcement and text
normalization) and converting a stored item back into local clipboard
content (ignoring items created by this same client). `AutoReceivePoller`
is the framework-agnostic polling/backoff state machine that drives
automatic receive on top of it.
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
from cbs.app.poller import AutoReceivePoller, PollOutcome, PollStatus
from cbs.app.service import ClipboardService

__all__ = [
    "AutoReceivePoller",
    "ClipboardService",
    "EmptyClipboardError",
    "MultipleFilesNotSupportedError",
    "PollOutcome",
    "PollStatus",
    "ReceiveResult",
    "ReceiveStatus",
    "SendRejectedError",
    "SizeLimitExceededError",
    "UnsupportedClipboardContentError",
]
