"""Background worker for GUI-triggered storage/NAS I/O.

QClipboard must only be used from the Qt main thread, but hashing and
writing/reading potentially large files over the NAS share should not
block it (docs/design/requirements_review_v0.1.md, 3.5). The pattern
used throughout the GUI layer is: do clipboard reads/writes on the main
thread, then hand the plain-data result to a CallableWorker for the
slow, Qt-free part.

Runs the callable on a plain Python thread (not a QThread subclass) and
reports its outcome back via a QTimer poll on the main thread. Earlier
attempts using a QThread subclass with deleteLater() hit a native crash
once a worker's lifecycle overlapped with starting another one from
inside a signal handler (see git history) — polling a plain
threading.Thread from the main thread sidesteps QThread's cross-thread
signal/ownership pitfalls entirely.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

_POLL_INTERVAL_MS = 20


class CallableWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, fn: Callable[[], Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._fn = fn
        self._thread: threading.Thread | None = None
        self._result: Any = None
        self._error: str | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._check_done)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._timer.start()

    def _run(self) -> None:
        try:
            self._result = self._fn()
        except Exception as exc:  # noqa: BLE001 - any failure must reach the GUI, not crash the thread
            self._error = str(exc)

    def _check_done(self) -> None:
        if self._thread is None or self._thread.is_alive():
            return
        self._timer.stop()
        if self._error is not None:
            self.failed.emit(self._error)
        else:
            self.succeeded.emit(self._result)
        self.finished.emit()
