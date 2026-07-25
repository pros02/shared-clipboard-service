from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from cbs.app.service import ClipboardService
from cbs.clipboard.models import ClipboardContent
from cbs.gui.history_dialog import HistoryDialog
from cbs.storage.nas_backend import NasStorageBackend
from tests.fakes import FakeClipboardAdapter


def test_history_dialog_lists_entries_and_copies_selected_row(qtbot: QtBot, tmp_path: Path) -> None:
    storage = NasStorageBackend(tmp_path / "nas")
    storage.prepare_for_startup()
    sender_clipboard = FakeClipboardAdapter(ClipboardContent.from_text("first"))
    sender = ClipboardService(
        storage,
        sender_clipboard,
        client_id="client-a",
        client_name="Ryzen7",
        received_files_dir=tmp_path / "received-a",
    )
    sender.send()
    sender_clipboard.content = ClipboardContent.from_text("second")
    sender.send()

    viewer_clipboard = FakeClipboardAdapter()
    viewer_service = ClipboardService(
        storage,
        viewer_clipboard,
        client_id="client-b",
        client_name="Ryzen3",
        received_files_dir=tmp_path / "received-b",
    )

    dialog = HistoryDialog(viewer_service, viewer_clipboard, limit=20)
    qtbot.addWidget(dialog)

    assert dialog._table.rowCount() == 2

    dialog._table.selectRow(0)
    dialog._on_copy_clicked()

    qtbot.waitUntil(lambda: "コピーしました" in dialog._status_label.text(), timeout=3000)
    assert viewer_clipboard.content is not None
    assert viewer_clipboard.content.text in {"first", "second"}
