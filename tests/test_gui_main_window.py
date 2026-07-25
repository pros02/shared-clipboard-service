"""GUI tests using pytest-qt.

Uses FakeClipboardAdapter (no real OS clipboard) so these tests are fast
and deterministic, exercising MainWindow's wiring to ClipboardService
and AutoReceivePoller, including the background-worker send/receive path.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from cbs.app.service import ClipboardService
from cbs.clipboard.models import ClipboardContent
from cbs.config.settings import Settings
from cbs.gui.main_window import MainWindow
from cbs.storage.nas_backend import NasStorageBackend
from tests.fakes import FakeClipboardAdapter


def _make_settings(*, nas_shared_folder: str = "", client_id: str = "client-a") -> Settings:
    return Settings(
        client_id=client_id,
        client_name="Ryzen7",
        nas_shared_folder=nas_shared_folder,
        auto_receive_enabled=False,
    )


def test_no_folder_configured_disables_actions(qtbot: QtBot, tmp_path: Path) -> None:
    settings = _make_settings()
    window = MainWindow(settings, tmp_path / "config.json", FakeClipboardAdapter())
    qtbot.addWidget(window)

    assert not window._send_button.isEnabled()
    assert not window._receive_button.isEnabled()
    assert not window._history_button.isEnabled()
    assert not window._auto_receive_checkbox.isEnabled()
    assert not window._interval_combo.isEnabled()


def test_folder_configured_enables_actions(qtbot: QtBot, tmp_path: Path) -> None:
    nas_dir = tmp_path / "nas"
    settings = _make_settings(nas_shared_folder=str(nas_dir))
    window = MainWindow(settings, tmp_path / "config.json", FakeClipboardAdapter())
    qtbot.addWidget(window)

    assert window._send_button.isEnabled()
    assert window._receive_button.isEnabled()
    assert window._history_button.isEnabled()
    assert (nas_dir / "current").is_dir()


def test_send_writes_item_to_storage(qtbot: QtBot, tmp_path: Path) -> None:
    nas_dir = tmp_path / "nas"
    settings = _make_settings(nas_shared_folder=str(nas_dir))
    clipboard = FakeClipboardAdapter(ClipboardContent.from_text("hello from GUI test"))
    window = MainWindow(settings, tmp_path / "config.json", clipboard)
    qtbot.addWidget(window)

    qtbot.mouseClick(window._send_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: "送信しました" in window._status_label.text(), timeout=3000)

    storage = NasStorageBackend(nas_dir)
    history = storage.list_history()
    assert len(history) == 1
    assert storage.read_object(history[0]) == b"hello from GUI test"


def test_send_with_empty_clipboard_shows_message_without_crashing(qtbot: QtBot, tmp_path: Path) -> None:
    nas_dir = tmp_path / "nas"
    settings = _make_settings(nas_shared_folder=str(nas_dir))
    window = MainWindow(settings, tmp_path / "config.json", FakeClipboardAdapter(None))
    qtbot.addWidget(window)

    qtbot.mouseClick(window._send_button, Qt.MouseButton.LeftButton)

    assert "送信できる内容がありません" in window._status_label.text()


def test_receive_from_other_client_writes_to_clipboard(qtbot: QtBot, tmp_path: Path) -> None:
    nas_dir = tmp_path / "nas"
    storage = NasStorageBackend(nas_dir)
    storage.prepare_for_startup()
    other_service = ClipboardService(
        storage,
        FakeClipboardAdapter(ClipboardContent.from_text("from another machine")),
        client_id="other-client",
        client_name="Ryzen3",
        received_files_dir=tmp_path / "received-other",
    )
    other_service.send()

    settings = _make_settings(nas_shared_folder=str(nas_dir), client_id="client-a")
    clipboard = FakeClipboardAdapter()
    window = MainWindow(settings, tmp_path / "config.json", clipboard)
    qtbot.addWidget(window)

    qtbot.mouseClick(window._receive_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: "受信しました" in window._status_label.text(), timeout=3000)

    assert clipboard.content is not None
    assert clipboard.content.text == "from another machine"


def test_receive_own_item_shows_message_without_writing(qtbot: QtBot, tmp_path: Path) -> None:
    nas_dir = tmp_path / "nas"
    settings = _make_settings(nas_shared_folder=str(nas_dir), client_id="client-a")
    clipboard = FakeClipboardAdapter(ClipboardContent.from_text("mine"))
    window = MainWindow(settings, tmp_path / "config.json", clipboard)
    qtbot.addWidget(window)

    qtbot.mouseClick(window._send_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: "送信しました" in window._status_label.text(), timeout=3000)

    clipboard.written.clear()
    qtbot.mouseClick(window._receive_button, Qt.MouseButton.LeftButton)

    assert "自分自身が送信したもの" in window._status_label.text()
    assert clipboard.written == []


def test_auto_receive_checkbox_starts_and_stops_polling(qtbot: QtBot, tmp_path: Path) -> None:
    nas_dir = tmp_path / "nas"
    settings = _make_settings(nas_shared_folder=str(nas_dir))
    window = MainWindow(settings, tmp_path / "config.json", FakeClipboardAdapter())
    qtbot.addWidget(window)

    assert window._poller is None

    window._auto_receive_checkbox.setChecked(True)
    assert window._poller is not None
    assert settings.auto_receive_enabled is True

    window._auto_receive_checkbox.setChecked(False)
    assert window._poller is None
    assert settings.auto_receive_enabled is False


def test_interval_change_updates_settings(qtbot: QtBot, tmp_path: Path) -> None:
    nas_dir = tmp_path / "nas"
    settings = _make_settings(nas_shared_folder=str(nas_dir))
    window = MainWindow(settings, tmp_path / "config.json", FakeClipboardAdapter())
    qtbot.addWidget(window)

    index = window._interval_combo.findData(5.0)
    assert index >= 0
    window._interval_combo.setCurrentIndex(index)

    assert settings.poll_interval_seconds == 5.0
