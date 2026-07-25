"""Settings dialog: history display count and start-on-login.

NAS folder selection and auto-receive/interval stay on MainWindow since
they're changed often; this dialog covers the more "set once" prefs
(docs/design/requirements_review_v0.1.md GUI/settings requirements).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cbs import platform
from cbs.config.settings import Settings, save_settings

_HISTORY_COUNT_MIN = 1
_HISTORY_COUNT_MAX = 200


def _resolve_launch_command() -> list[str]:
    """Return the command that should relaunch this app at login.

    A PyInstaller-frozen build's sys.executable *is* the app itself, with
    no separate "cbs" module to invoke via -m; a source/venv install
    needs "-m cbs" to tell the interpreter what to run.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "cbs"]


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        settings_path: Path,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("設定")
        self._settings = settings
        self._settings_path = settings_path

        self._history_count_spin = QSpinBox()
        self._history_count_spin.setRange(_HISTORY_COUNT_MIN, _HISTORY_COUNT_MAX)
        self._history_count_spin.setValue(settings.history_display_count)

        self._start_on_login_checkbox = QCheckBox("ログイン時に自動起動する")
        self._start_on_login_checkbox.setChecked(platform.is_start_on_login_enabled())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("履歴表示件数:", self._history_count_spin)
        form.addRow(self._start_on_login_checkbox)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        self._settings.history_display_count = self._history_count_spin.value()

        want_enabled = self._start_on_login_checkbox.isChecked()
        if want_enabled:
            platform.enable_start_on_login(_resolve_launch_command())
        else:
            platform.disable_start_on_login()
        self._settings.start_on_login = want_enabled

        save_settings(self._settings_path, self._settings)
        self.accept()
