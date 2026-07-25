"""Result types for ClipboardService.receive()."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cbs.storage.models import ClipboardItemMetadata


class ReceiveStatus(str, Enum):
    RECEIVED = "received"
    IGNORED_OWN_CLIENT = "ignored_own_client"
    NOTHING_AVAILABLE = "nothing_available"


@dataclass(frozen=True)
class ReceiveResult:
    status: ReceiveStatus
    metadata: ClipboardItemMetadata | None
