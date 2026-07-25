"""Main application window.

Presentation only: business rules (size limits, same-client filtering,
retention, polling/backoff) all live in cbs.app/cbs.storage. This module
wires user actions to ClipboardService/AutoReceivePoller and renders
their results — it does not implement any of those rules itself
(CLAUDE.md: "do not put business logic directly in GUI classes").
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cbs import platform
from cbs.app.errors import EmptyClipboardError
from cbs.app.poller import AutoReceivePoller, PollStatus
from cbs.app.service import ClipboardService
from cbs.clipboard.base import ClipboardAdapter
from cbs.clipboard.models import ClipboardContent
from cbs.config.settings import POLL_INTERVAL_CHOICES, Settings, save_settings
from cbs.domain import ItemType
from cbs.gui.formatting import type_label
from cbs.gui.history_dialog import HistoryDialog
from cbs.gui.workers import CallableWorker
from cbs.storage.models import ClipboardItemMetadata
from cbs.storage.nas_backend import NasStorageBackend

logger = logging.getLogger(__name__)

_PREVIEW_TEXT_CHARS = 500
_PREVIEW_IMAGE_SIZE = 240


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: Settings,
        settings_path: Path,
        clipboard: ClipboardAdapter,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Shared Clipboard Service")
        self.resize(560, 420)

        self._settings = settings
        self._settings_path = settings_path
        self._clipboard = clipboard
        self._service: ClipboardService | None = None
        self._poller: AutoReceivePoller | None = None
        self._active_worker: CallableWorker | None = None
        self._preview_worker: CallableWorker | None = None

        self._build_widgets()

        self._poll_timer = QTimer(self)
        self._poll_timer.setSingleShot(True)
        self._poll_timer.timeout.connect(self._on_poll_timer_tick)

        if settings.nas_shared_folder:
            self._configure_storage(Path(settings.nas_shared_folder))
        else:
            self._update_action_buttons_enabled()
            self._refresh_preview()

    # -- widget construction -------------------------------------------------

    def _build_widgets(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        folder_row = QHBoxLayout()
        self._folder_edit = QLineEdit(self._settings.nas_shared_folder)
        self._folder_edit.setReadOnly(True)
        browse_button = QPushButton("参照...")
        browse_button.clicked.connect(self._on_browse_clicked)
        folder_row.addWidget(QLabel("共有フォルダ:"))
        folder_row.addWidget(self._folder_edit, 1)
        folder_row.addWidget(browse_button)
        layout.addLayout(folder_row)

        preview_group = QGroupBox("現在の内容")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_info_label = QLabel("")
        self._preview_content_label = QLabel("")
        self._preview_content_label.setWordWrap(True)
        self._preview_content_label.setMinimumHeight(120)
        self._preview_content_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        refresh_button = QPushButton("更新")
        refresh_button.clicked.connect(self._refresh_preview)
        preview_layout.addWidget(self._preview_info_label)
        preview_layout.addWidget(self._preview_content_label, 1)
        preview_layout.addWidget(refresh_button)
        layout.addWidget(preview_group, 1)

        button_row = QHBoxLayout()
        self._send_button = QPushButton("送信")
        self._send_button.clicked.connect(self._on_send_clicked)
        self._receive_button = QPushButton("受信")
        self._receive_button.clicked.connect(self._on_receive_clicked)
        self._history_button = QPushButton("履歴")
        self._history_button.clicked.connect(self._on_history_clicked)
        button_row.addWidget(self._send_button)
        button_row.addWidget(self._receive_button)
        button_row.addWidget(self._history_button)
        layout.addLayout(button_row)

        auto_row = QHBoxLayout()
        self._auto_receive_checkbox = QCheckBox("自動受信")
        self._auto_receive_checkbox.setChecked(self._settings.auto_receive_enabled)
        self._auto_receive_checkbox.toggled.connect(self._on_auto_receive_toggled)
        self._interval_combo = QComboBox()
        for choice in POLL_INTERVAL_CHOICES:
            self._interval_combo.addItem(f"{choice:g}秒間隔", choice)
        index = self._interval_combo.findData(self._settings.poll_interval_seconds)
        self._interval_combo.setCurrentIndex(index if index >= 0 else 1)
        self._interval_combo.currentIndexChanged.connect(self._on_interval_changed)
        auto_row.addWidget(self._auto_receive_checkbox)
        auto_row.addWidget(self._interval_combo)
        auto_row.addStretch(1)
        layout.addLayout(auto_row)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

    # -- storage/service configuration ---------------------------------------

    def _configure_storage(self, folder: Path) -> None:
        storage = NasStorageBackend(
            folder,
            max_retained_items=self._settings.max_retained_items,
            max_retained_total_bytes=self._settings.max_retained_total_bytes,
        )
        try:
            storage.prepare_for_startup()
        except OSError as exc:
            self._set_status(f"共有フォルダを準備できません: {exc}")
            self._service = None
            self._update_action_buttons_enabled()
            return

        self._service = ClipboardService(
            storage,
            self._clipboard,
            client_id=self._settings.client_id,
            client_name=self._settings.client_name,
            received_files_dir=platform.get_received_files_dir(),
        )
        self._update_action_buttons_enabled()
        self._refresh_preview()
        if self._settings.auto_receive_enabled:
            self._start_polling()

    def _save_settings(self) -> None:
        try:
            save_settings(self._settings_path, self._settings)
        except OSError:
            logger.exception("Failed to persist settings to %s", self._settings_path)

    def _update_action_buttons_enabled(self) -> None:
        enabled = self._service is not None
        self._send_button.setEnabled(enabled)
        self._receive_button.setEnabled(enabled)
        self._history_button.setEnabled(enabled)
        self._auto_receive_checkbox.setEnabled(enabled)

    # -- folder selection ------------------------------------------------------

    def _on_browse_clicked(self) -> None:
        start_dir = self._settings.nas_shared_folder or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "共有フォルダを選択", start_dir)
        if not folder:
            return
        self._settings.nas_shared_folder = folder
        self._save_settings()
        self._folder_edit.setText(folder)
        self._stop_polling()
        self._configure_storage(Path(folder))

    # -- send ------------------------------------------------------------------

    def _on_send_clicked(self) -> None:
        if self._service is None:
            return
        content = self._clipboard.read()
        if content is None:
            self._set_status(str(EmptyClipboardError()))
            return

        service = self._service
        self._set_busy(True)
        self._set_status("送信中...")
        worker = CallableWorker(lambda: service.send_content(content))
        worker.succeeded.connect(self._on_send_succeeded)
        worker.failed.connect(self._on_send_failed)
        worker.finished.connect(self._on_worker_finished)
        worker.finished.connect(worker.deleteLater)
        self._active_worker = worker
        worker.start()

    def _on_send_succeeded(self, metadata: object) -> None:
        if isinstance(metadata, ClipboardItemMetadata):
            self._set_status(f"送信しました: {metadata.original_name}")
        self._refresh_preview()

    def _on_send_failed(self, message: str) -> None:
        self._set_status(f"送信できません: {message}")

    # -- receive -----------------------------------------------------------------

    def _on_receive_clicked(self) -> None:
        if self._service is None:
            return
        service = self._service
        try:
            current = service.peek_current()
        except OSError as exc:
            self._set_status(f"NASにアクセスできません: {exc}")
            return
        if current is None:
            self._set_status("受信できる項目がありません。")
            return
        if current.client_id == service.client_id:
            self._set_status("最新の項目は自分自身が送信したものです。")
            return

        self._set_busy(True)
        self._set_status("受信中...")
        worker = CallableWorker(lambda: service.fetch_content_for(current))
        worker.succeeded.connect(lambda content: self._on_receive_fetched(current, content))
        worker.failed.connect(self._on_receive_failed)
        worker.finished.connect(self._on_worker_finished)
        worker.finished.connect(worker.deleteLater)
        self._active_worker = worker
        worker.start()

    def _on_receive_fetched(self, metadata: ClipboardItemMetadata, content: object) -> None:
        if isinstance(content, ClipboardContent):
            self._clipboard.write(content)
            self._set_status(f"受信しました: {metadata.original_name}")
        self._refresh_preview()

    def _on_receive_failed(self, message: str) -> None:
        self._set_status(f"受信できません: {message}")

    def _on_worker_finished(self) -> None:
        self._set_busy(False)
        self._active_worker = None

    # -- history -----------------------------------------------------------------

    def _on_history_clicked(self) -> None:
        if self._service is None:
            return
        dialog = HistoryDialog(
            self._service,
            self._clipboard,
            limit=self._settings.history_display_count,
            parent=self,
        )
        dialog.exec()

    # -- preview -----------------------------------------------------------------

    def _refresh_preview(self) -> None:
        if self._service is None:
            self._preview_info_label.setText("共有フォルダが設定されていません。")
            self._preview_content_label.setText("")
            self._preview_content_label.setPixmap(QPixmap())
            return

        try:
            current = self._service.peek_current()
        except OSError as exc:
            self._preview_info_label.setText(f"NASにアクセスできません: {exc}")
            return

        if current is None:
            self._preview_info_label.setText("現在共有されている項目はありません。")
            self._preview_content_label.setText("")
            self._preview_content_label.setPixmap(QPixmap())
            return

        self._preview_info_label.setText(
            f"{type_label(current.type)} | 送信元: {current.client_name} | {current.created_at_utc}"
        )

        if current.type is ItemType.FILE:
            self._preview_content_label.setPixmap(QPixmap())
            self._preview_content_label.setText(f"{current.original_name} ({current.size_bytes:,} bytes)")
            return

        service = self._service
        worker = CallableWorker(lambda: service.fetch_content_for(current))
        worker.succeeded.connect(self._on_preview_fetched)
        worker.failed.connect(lambda msg: self._preview_content_label.setText(f"プレビュー取得失敗: {msg}"))
        worker.finished.connect(self._on_preview_worker_finished)
        worker.finished.connect(worker.deleteLater)
        self._preview_worker = worker
        worker.start()

    def _on_preview_worker_finished(self) -> None:
        self._preview_worker = None

    def _on_preview_fetched(self, content: object) -> None:
        if not isinstance(content, ClipboardContent):
            return
        if content.type is ItemType.TEXT and content.text is not None:
            text = content.text
            preview = text if len(text) <= _PREVIEW_TEXT_CHARS else text[:_PREVIEW_TEXT_CHARS] + "..."
            self._preview_content_label.setPixmap(QPixmap())
            self._preview_content_label.setText(preview)
        elif content.type is ItemType.IMAGE and content.image_png is not None:
            pixmap = QPixmap()
            pixmap.loadFromData(content.image_png)
            scaled = pixmap.scaled(
                _PREVIEW_IMAGE_SIZE,
                _PREVIEW_IMAGE_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._preview_content_label.setText("")
            self._preview_content_label.setPixmap(scaled)

    # -- auto-receive polling -----------------------------------------------------

    def _current_poll_interval(self) -> float:
        data = self._interval_combo.currentData()
        return float(data) if data is not None else POLL_INTERVAL_CHOICES[1]

    def _start_polling(self) -> None:
        if self._service is None:
            return
        self._poller = AutoReceivePoller(self._service, interval_seconds=self._current_poll_interval())
        self._schedule_next_poll(immediate=True)

    def _stop_polling(self) -> None:
        self._poll_timer.stop()
        self._poller = None

    def _schedule_next_poll(self, *, immediate: bool = False) -> None:
        if self._poller is None:
            return
        delay_ms = 0 if immediate else int(self._poller.next_interval_seconds * 1000)
        self._poll_timer.start(delay_ms)

    def _on_poll_timer_tick(self) -> None:
        if self._poller is None:
            return
        outcome = self._poller.poll_once()
        if outcome.status is PollStatus.RECEIVED and outcome.metadata is not None:
            self._set_status(f"自動受信しました: {outcome.metadata.original_name}")
            self._refresh_preview()
        elif outcome.status is PollStatus.ERROR:
            self._set_status(f"自動受信エラー: {outcome.error}")
        self._schedule_next_poll()

    def _on_auto_receive_toggled(self, checked: bool) -> None:
        self._settings.auto_receive_enabled = checked
        self._save_settings()
        if checked:
            self._start_polling()
        else:
            self._stop_polling()

    def _on_interval_changed(self, _index: int) -> None:
        self._settings.poll_interval_seconds = self._current_poll_interval()
        self._save_settings()
        if self._poller is not None:
            self._start_polling()

    # -- misc ------------------------------------------------------------------

    def _set_busy(self, busy: bool) -> None:
        enabled = not busy and self._service is not None
        self._send_button.setEnabled(enabled)
        self._receive_button.setEnabled(enabled)

    def _set_status(self, message: str) -> None:
        self._status_label.setText(message)
        logger.info(message)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._poll_timer.stop()
        super().closeEvent(event)
