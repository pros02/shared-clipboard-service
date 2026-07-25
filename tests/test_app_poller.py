from __future__ import annotations

import time
from pathlib import Path

from cbs.app.poller import AutoReceivePoller, PollStatus
from cbs.app.service import ClipboardService
from cbs.clipboard.models import ClipboardContent
from cbs.storage.base import StorageBackend
from cbs.storage.models import ClipboardItemMetadata, NewClipboardItem
from cbs.storage.nas_backend import NasStorageBackend
from tests.fakes import FakeClipboardAdapter


class FailingStorageBackend(StorageBackend):
    """A storage backend whose read_current() always raises, simulating an
    unreachable NAS share."""

    def prepare_for_startup(self) -> None:
        pass

    def write_item(self, item: NewClipboardItem) -> ClipboardItemMetadata:
        raise NotImplementedError

    def read_current(self) -> ClipboardItemMetadata | None:
        raise OSError("simulated NAS disconnect")

    def read_object(self, item: ClipboardItemMetadata) -> bytes:
        raise NotImplementedError

    def list_history(self, limit: int | None = None) -> list[ClipboardItemMetadata]:
        return []


class FlakyStorageBackend(StorageBackend):
    """Delegates to a real backend, but fails read_current() a fixed number
    of times first — simulating a NAS share that reconnects."""

    def __init__(self, delegate: StorageBackend, *, fail_times: int) -> None:
        self._delegate = delegate
        self._remaining_failures = fail_times

    def prepare_for_startup(self) -> None:
        self._delegate.prepare_for_startup()

    def write_item(self, item: NewClipboardItem) -> ClipboardItemMetadata:
        return self._delegate.write_item(item)

    def read_current(self) -> ClipboardItemMetadata | None:
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise OSError("simulated transient NAS disconnect")
        return self._delegate.read_current()

    def read_object(self, item: ClipboardItemMetadata) -> bytes:
        return self._delegate.read_object(item)

    def list_history(self, limit: int | None = None) -> list[ClipboardItemMetadata]:
        return self._delegate.list_history(limit)


def _make_poller(
    tmp_path: Path, *, client_id: str, interval_seconds: float = 1.0
) -> tuple[AutoReceivePoller, NasStorageBackend, FakeClipboardAdapter]:
    storage = NasStorageBackend(tmp_path / "nas")
    storage.prepare_for_startup()
    adapter = FakeClipboardAdapter()
    service = ClipboardService(
        storage,
        adapter,
        client_id=client_id,
        client_name=client_id,
        received_files_dir=tmp_path / f"received-{client_id}",
    )
    poller = AutoReceivePoller(service, interval_seconds=interval_seconds)
    return poller, storage, adapter


def test_poll_once_nothing_available(tmp_path: Path) -> None:
    poller, _, adapter = _make_poller(tmp_path, client_id="client-a")

    outcome = poller.poll_once()

    assert outcome.status is PollStatus.NOTHING_AVAILABLE
    assert adapter.written == []
    assert poller.next_interval_seconds == 1.0


def test_poll_once_ignores_own_client_item(tmp_path: Path) -> None:
    poller, storage, adapter = _make_poller(tmp_path, client_id="client-a", interval_seconds=1.0)
    sender = ClipboardService(
        storage,
        FakeClipboardAdapter(ClipboardContent.from_text("mine")),
        client_id="client-a",
        client_name="client-a",
        received_files_dir=tmp_path / "received-sender",
    )
    sender.send()

    outcome = poller.poll_once()

    assert outcome.status is PollStatus.IGNORED_OWN_CLIENT
    assert adapter.written == []


def test_poll_once_receives_new_item_from_other_client(tmp_path: Path) -> None:
    # poll_once() never touches the clipboard itself (so it's safe to run
    # off the main thread) — it returns content for the *caller* to write,
    # same as a real GUI would do on poll_once()'s success signal.
    poller, storage, adapter = _make_poller(tmp_path, client_id="client-b")
    sender = ClipboardService(
        storage,
        FakeClipboardAdapter(ClipboardContent.from_text("hello")),
        client_id="client-a",
        client_name="client-a",
        received_files_dir=tmp_path / "received-sender",
    )
    sender.send()

    outcome = poller.poll_once()

    assert outcome.status is PollStatus.RECEIVED
    assert outcome.content is not None
    assert outcome.content.text == "hello"
    assert adapter.written == []  # poller itself never writes


def test_poll_once_does_not_rewrite_unchanged_item(tmp_path: Path) -> None:
    poller, storage, _adapter = _make_poller(tmp_path, client_id="client-b")
    sender = ClipboardService(
        storage,
        FakeClipboardAdapter(ClipboardContent.from_text("hello")),
        client_id="client-a",
        client_name="client-a",
        received_files_dir=tmp_path / "received-sender",
    )
    sender.send()

    first = poller.poll_once()
    second = poller.poll_once()

    assert first.status is PollStatus.RECEIVED
    assert first.content is not None
    assert second.status is PollStatus.ALREADY_PROCESSED
    assert second.content is None


def test_poll_once_receives_replacement_item(tmp_path: Path) -> None:
    poller, storage, _adapter = _make_poller(tmp_path, client_id="client-b")
    sender_adapter = FakeClipboardAdapter(ClipboardContent.from_text("first"))
    sender = ClipboardService(
        storage,
        sender_adapter,
        client_id="client-a",
        client_name="client-a",
        received_files_dir=tmp_path / "received-sender",
    )
    sender.send()
    poller.poll_once()

    sender_adapter.content = ClipboardContent.from_text("second")
    sender.send()
    outcome = poller.poll_once()

    assert outcome.status is PollStatus.RECEIVED
    assert outcome.content is not None
    assert outcome.content.text == "second"


class SlowStorageBackend(StorageBackend):
    """Simulates an unreachable NAS *host* (as opposed to a missing share
    on a reachable one): read_current() doesn't raise, it just takes a
    long time, matching what a real ~21s Windows network timeout looks
    like from the caller's side. See poller.py's module docstring."""

    def __init__(self, delay_seconds: float) -> None:
        self._delay_seconds = delay_seconds

    def prepare_for_startup(self) -> None:
        pass

    def write_item(self, item: NewClipboardItem) -> ClipboardItemMetadata:
        raise NotImplementedError

    def read_current(self) -> ClipboardItemMetadata | None:
        time.sleep(self._delay_seconds)
        return None

    def read_object(self, item: ClipboardItemMetadata) -> bytes:
        raise NotImplementedError

    def list_history(self, limit: int | None = None) -> list[ClipboardItemMetadata]:
        return []


def test_poll_once_treats_slow_response_as_failure_even_without_exception(tmp_path: Path) -> None:
    storage = SlowStorageBackend(delay_seconds=3.2)
    adapter = FakeClipboardAdapter()
    service = ClipboardService(
        storage,
        adapter,
        client_id="client-a",
        client_name="client-a",
        received_files_dir=tmp_path / "received",
    )
    poller = AutoReceivePoller(service, interval_seconds=1.0)

    outcome = poller.poll_once()

    assert outcome.status is PollStatus.ERROR
    assert outcome.error is not None
    assert poller.next_interval_seconds == 5.0


def test_poll_once_error_backs_off_up_to_cap(tmp_path: Path) -> None:
    storage = FailingStorageBackend()
    adapter = FakeClipboardAdapter()
    service = ClipboardService(
        storage,
        adapter,
        client_id="client-a",
        client_name="client-a",
        received_files_dir=tmp_path / "received",
    )
    poller = AutoReceivePoller(service, interval_seconds=1.0)

    outcomes_and_intervals = []
    for _ in range(5):
        outcome = poller.poll_once()
        outcomes_and_intervals.append((outcome.status, poller.next_interval_seconds))

    assert [status for status, _ in outcomes_and_intervals] == [PollStatus.ERROR] * 5
    assert [interval for _, interval in outcomes_and_intervals] == [5.0, 10.0, 20.0, 30.0, 30.0]


def test_poll_once_recovers_interval_after_success(tmp_path: Path) -> None:
    real_storage = NasStorageBackend(tmp_path / "nas")
    real_storage.prepare_for_startup()
    flaky = FlakyStorageBackend(real_storage, fail_times=2)
    adapter = FakeClipboardAdapter()
    service = ClipboardService(
        flaky,
        adapter,
        client_id="client-a",
        client_name="client-a",
        received_files_dir=tmp_path / "received",
    )
    poller = AutoReceivePoller(service, interval_seconds=2.0)

    first = poller.poll_once()
    assert first.status is PollStatus.ERROR
    assert poller.next_interval_seconds == 5.0

    second = poller.poll_once()
    assert second.status is PollStatus.ERROR
    assert poller.next_interval_seconds == 10.0

    third = poller.poll_once()
    assert third.status is PollStatus.NOTHING_AVAILABLE
    assert poller.next_interval_seconds == 2.0
