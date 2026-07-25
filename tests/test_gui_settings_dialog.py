from __future__ import annotations

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from cbs import platform
from cbs.config.settings import Settings
from cbs.gui.settings_dialog import SettingsDialog


def test_dialog_reflects_current_state(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(platform, "is_start_on_login_enabled", lambda: True)
    settings = Settings(history_display_count=42)

    dialog = SettingsDialog(settings, tmp_path / "config.json")
    qtbot.addWidget(dialog)

    assert dialog._history_count_spin.value() == 42
    assert dialog._start_on_login_checkbox.isChecked() is True


def test_accept_saves_history_count_and_enables_autostart(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(platform, "is_start_on_login_enabled", lambda: False)
    enabled_with: list[list[str]] = []
    monkeypatch.setattr(platform, "enable_start_on_login", lambda command: enabled_with.append(command))

    settings = Settings(history_display_count=10)
    settings_path = tmp_path / "config.json"
    dialog = SettingsDialog(settings, settings_path)
    qtbot.addWidget(dialog)

    dialog._history_count_spin.setValue(77)
    dialog._start_on_login_checkbox.setChecked(True)
    dialog._on_accept()

    assert settings.history_display_count == 77
    assert settings.start_on_login is True
    assert len(enabled_with) == 1
    assert settings_path.exists()


def test_accept_disables_autostart_when_unchecked(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(platform, "is_start_on_login_enabled", lambda: True)
    disabled_calls: list[bool] = []
    monkeypatch.setattr(platform, "disable_start_on_login", lambda: disabled_calls.append(True))

    settings = Settings()
    dialog = SettingsDialog(settings, tmp_path / "config.json")
    qtbot.addWidget(dialog)

    dialog._start_on_login_checkbox.setChecked(False)
    dialog._on_accept()

    assert settings.start_on_login is False
    assert len(disabled_calls) == 1
