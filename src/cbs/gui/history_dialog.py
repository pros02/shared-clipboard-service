"""History dialog: browse recent items and re-copy one to the local clipboard."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cbs.app.service import ClipboardService
from cbs.clipboard.base import ClipboardAdapter
from cbs.clipboard.models import ClipboardContent
from cbs.gui.formatting import type_label
from cbs.gui.workers import CallableWorker
from cbs.storage.models import ClipboardItemMetadata


class HistoryDialog(QDialog):
    def __init__(
        self,
        service: ClipboardService,
        clipboard: ClipboardAdapter,
        *,
        limit: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("履歴")
        self.resize(560, 360)

        self._service = service
        self._clipboard = clipboard
        self._limit = limit
        self._entries: list[ClipboardItemMetadata] = []
        self._worker: CallableWorker | None = None

        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels(["種別", "送信元", "日時 (UTC)", "名前"])
        header = self._table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self._status_label = QLabel("")
        copy_button = QPushButton("クリップボードへコピー")
        copy_button.clicked.connect(self._on_copy_clicked)
        refresh_button = QPushButton("更新")
        refresh_button.clicked.connect(self._reload)
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.close)

        button_row = QHBoxLayout()
        button_row.addWidget(copy_button)
        button_row.addWidget(refresh_button)
        button_row.addStretch()
        button_row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addWidget(self._status_label)
        layout.addLayout(button_row)

        self._reload()

    def _reload(self) -> None:
        try:
            self._entries = self._service.list_history(limit=self._limit)
        except OSError as exc:
            self._status_label.setText(f"履歴を取得できません: {exc}")
            self._entries = []

        self._table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            self._table.setItem(row, 0, QTableWidgetItem(type_label(entry.type)))
            self._table.setItem(row, 1, QTableWidgetItem(entry.client_name))
            self._table.setItem(row, 2, QTableWidgetItem(entry.created_at_utc))
            self._table.setItem(row, 3, QTableWidgetItem(entry.original_name))

    def _on_copy_clicked(self) -> None:
        selection_model = self._table.selectionModel()
        rows = selection_model.selectedRows() if selection_model is not None else []
        if not rows:
            self._status_label.setText("項目を選択してください。")
            return
        metadata = self._entries[rows[0].row()]

        self._status_label.setText("コピー中...")
        worker = CallableWorker(lambda: self._service.fetch_content_for(metadata))
        worker.succeeded.connect(self._on_fetch_succeeded)
        worker.failed.connect(self._on_fetch_failed)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _on_fetch_succeeded(self, content: object) -> None:
        if isinstance(content, ClipboardContent):
            self._clipboard.write(content)
            self._status_label.setText("クリップボードにコピーしました。")

    def _on_fetch_failed(self, message: str) -> None:
        self._status_label.setText(f"コピーに失敗しました: {message}")
