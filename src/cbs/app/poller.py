"""Automatic-receive polling state machine.

Framework-agnostic: this class does no sleeping/threading/Qt itself. A
caller (a GUI QTimer, a background thread, or a test loop) is expected
to call poll_once() repeatedly, waiting next_interval_seconds between
calls. That external loop is what actually drives "automatic" receive —
this class only decides what a given tick should do and how long to
wait before the next one, per docs/design/requirements_review_v0.1.md
section 3.1: a configurable base interval (0.5/1/2/5s) that backs off
to 5s, then up to 30s, while the NAS is unreachable, and recovers to the
configured interval once it's reachable again.

Whether writing to the clipboard from an automatic (non-user-triggered)
poll works on every platform is untested as of Phase 4 — see the
Wayland/GNOME focus finding in the design review for Phase 2. Verify
this on Ubuntu once the poller is wired into a real GUI event loop.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from cbs.app.models import ReceiveStatus
from cbs.app.service import ClipboardService
from cbs.storage.models import ClipboardItemMetadata

logger = logging.getLogger(__name__)

_DISCONNECTED_INITIAL_INTERVAL_SECONDS = 5.0
_DISCONNECTED_MAX_INTERVAL_SECONDS = 30.0


class PollStatus(str, Enum):
    RECEIVED = "received"
    ALREADY_PROCESSED = "already_processed"
    IGNORED_OWN_CLIENT = "ignored_own_client"
    NOTHING_AVAILABLE = "nothing_available"
    ERROR = "error"


@dataclass(frozen=True)
class PollOutcome:
    status: PollStatus
    metadata: ClipboardItemMetadata | None = None
    error: str | None = None


class AutoReceivePoller:
    def __init__(self, service: ClipboardService, *, interval_seconds: float) -> None:
        self._service = service
        self._configured_interval = interval_seconds
        self._current_interval = interval_seconds
        self._consecutive_failures = 0
        self._last_item_id: str | None = None

    @property
    def next_interval_seconds(self) -> float:
        return self._current_interval

    def poll_once(self) -> PollOutcome:
        try:
            current = self._service.peek_current()
        except OSError as exc:
            self._register_failure()
            logger.warning("Auto-receive poll failed (NAS unreachable?): %s", exc)
            return PollOutcome(status=PollStatus.ERROR, error=str(exc))

        self._register_success()

        if current is None:
            return PollOutcome(status=PollStatus.NOTHING_AVAILABLE)

        if current.client_id == self._service.client_id:
            return PollOutcome(status=PollStatus.IGNORED_OWN_CLIENT, metadata=current)

        if current.item_id == self._last_item_id:
            return PollOutcome(status=PollStatus.ALREADY_PROCESSED, metadata=current)

        result = self._service.receive()
        if result.metadata is not None:
            self._last_item_id = result.metadata.item_id

        if result.status is ReceiveStatus.RECEIVED:
            return PollOutcome(status=PollStatus.RECEIVED, metadata=result.metadata)
        if result.status is ReceiveStatus.IGNORED_OWN_CLIENT:
            return PollOutcome(status=PollStatus.IGNORED_OWN_CLIENT, metadata=result.metadata)
        return PollOutcome(status=PollStatus.NOTHING_AVAILABLE, metadata=result.metadata)

    def _register_failure(self) -> None:
        if self._consecutive_failures == 0:
            self._current_interval = _DISCONNECTED_INITIAL_INTERVAL_SECONDS
        else:
            self._current_interval = min(
                _DISCONNECTED_MAX_INTERVAL_SECONDS, self._current_interval * 2
            )
        self._consecutive_failures += 1

    def _register_success(self) -> None:
        self._consecutive_failures = 0
        self._current_interval = self._configured_interval
