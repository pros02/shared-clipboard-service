"""Automatic-receive polling state machine.

Framework-agnostic: this class does no sleeping/threading/Qt itself, and
— unlike ClipboardService.receive() — never touches the clipboard. A
caller (a GUI QTimer, a background thread, or a test loop) is expected
to call poll_once() repeatedly, waiting next_interval_seconds between
calls, and to write outcome.content to the clipboard itself when
outcome.status is RECEIVED. That split matters because poll_once() can
block for a long time (see below), so it must be safe to run entirely
off the Qt main thread; only the final clipboard write needs that
thread (QClipboard is not thread-safe).

Backoff, per docs/design/requirements_review_v0.1.md section 3.1: a
configurable base interval (0.5/1/2/5s) that backs off to 5s, then up
to 30s, while the NAS is unreachable, and recovers to the configured
interval once it's reachable again.

A live test against an unreachable NAS host (not just a missing share
on a reachable one) found that Path.exists()/stat() do not raise for
that failure mode on Windows — they silently return "doesn't exist"
after a real ~21s network timeout. That means the naive
"except OSError: back off" logic never triggers for the single most
realistic disconnect scenario (NAS powered off / cable unplugged), and
the fact that it takes ~21s per attempt makes the same call unsafe to
run on the GUI's main thread. Detect that slow-response case
heuristically instead: any peek_current() call taking longer than
_SLOW_RESPONSE_THRESHOLD_SECONDS is treated as a failure for backoff
purposes even if it didn't raise. A healthy read is a small local JSON
file read and should be near-instant, so this shouldn't trigger for
legitimate operation.

Whether writing to the clipboard from an automatic (non-user-triggered)
poll works on every platform is untested as of Phase 4 — see the
Wayland/GNOME focus finding in the design review for Phase 2.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum

from cbs.app.service import ClipboardService
from cbs.clipboard.models import ClipboardContent
from cbs.storage.models import ClipboardItemMetadata

logger = logging.getLogger(__name__)

_DISCONNECTED_INITIAL_INTERVAL_SECONDS = 5.0
_DISCONNECTED_MAX_INTERVAL_SECONDS = 30.0
_SLOW_RESPONSE_THRESHOLD_SECONDS = 3.0


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
    content: ClipboardContent | None = None
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
        start = time.monotonic()
        try:
            current = self._service.peek_current()
        except OSError as exc:
            self._register_failure()
            logger.warning("Auto-receive poll failed (NAS unreachable?): %s", exc)
            return PollOutcome(status=PollStatus.ERROR, error=str(exc))

        elapsed = time.monotonic() - start
        if elapsed > _SLOW_RESPONSE_THRESHOLD_SECONDS:
            self._register_failure()
            message = f"NASの応答がありません({elapsed:.1f}秒でタイムアウト)"
            logger.warning("Auto-receive poll: %s", message)
            return PollOutcome(status=PollStatus.ERROR, error=message)

        self._register_success()

        if current is None:
            return PollOutcome(status=PollStatus.NOTHING_AVAILABLE)

        if current.client_id == self._service.client_id:
            return PollOutcome(status=PollStatus.IGNORED_OWN_CLIENT, metadata=current)

        if current.item_id == self._last_item_id:
            return PollOutcome(status=PollStatus.ALREADY_PROCESSED, metadata=current)

        try:
            content = self._service.fetch_content_for(current)
        except OSError as exc:
            self._register_failure()
            logger.warning("Auto-receive poll failed to fetch item content: %s", exc)
            return PollOutcome(status=PollStatus.ERROR, error=str(exc))

        self._last_item_id = current.item_id
        return PollOutcome(status=PollStatus.RECEIVED, metadata=current, content=content)

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
