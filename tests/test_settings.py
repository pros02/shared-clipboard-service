from __future__ import annotations

import json
from pathlib import Path

from cbs.config.settings import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    POLL_INTERVAL_CHOICES,
    Settings,
    load_settings,
    save_settings,
)


def test_load_creates_default_file_when_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"

    settings = load_settings(config_path)

    assert config_path.exists()
    assert settings.poll_interval_seconds == DEFAULT_POLL_INTERVAL_SECONDS
    assert settings.client_id


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    original = Settings(
        nas_shared_folder="/mnt/networkstorage/sharedclipboard",
        auto_receive_enabled=True,
    )

    save_settings(config_path, original)
    loaded = load_settings(config_path)

    assert loaded.nas_shared_folder == original.nas_shared_folder
    assert loaded.auto_receive_enabled is True
    assert loaded.client_id == original.client_id


def test_malformed_json_falls_back_to_defaults_and_is_backed_up(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{not valid json", encoding="utf-8")

    settings = load_settings(config_path)

    assert settings.nas_shared_folder == ""
    assert settings.poll_interval_seconds == DEFAULT_POLL_INTERVAL_SECONDS
    assert settings.client_id

    backups = list(tmp_path.glob("config.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{not valid json"


def test_invalid_poll_interval_is_corrected_and_persisted(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"poll_interval_seconds": 3.0}), encoding="utf-8")

    settings = load_settings(config_path)

    assert settings.poll_interval_seconds == DEFAULT_POLL_INTERVAL_SECONDS
    assert settings.poll_interval_seconds in POLL_INTERVAL_CHOICES

    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted["poll_interval_seconds"] == DEFAULT_POLL_INTERVAL_SECONDS


def test_client_id_persists_across_loads(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"

    first = load_settings(config_path)
    second = load_settings(config_path)

    assert first.client_id == second.client_id
