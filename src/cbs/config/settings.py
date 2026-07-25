"""Local application settings: schema, defaults, load/save.

This is distinct from the NAS-side ``current.json`` clipboard-item metadata
schema (see docs/design/requirements_review_v0.1.md, section 3.3). Settings
here are per-machine and are never synced through the shared folder.
"""
from __future__ import annotations

import json
import logging
import socket
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cbs.util.atomic_io import atomic_write_text

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
POLL_INTERVAL_CHOICES: tuple[float, ...] = (0.5, 1.0, 2.0, 5.0)
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_HISTORY_DISPLAY_COUNT = 20
DEFAULT_MAX_RETAINED_ITEMS = 50
DEFAULT_MAX_RETAINED_TOTAL_BYTES = 2 * 1024**3  # 2 GB
DEFAULT_LOG_LEVEL = "INFO"


@dataclass
class Settings:
    schema_version: int = SCHEMA_VERSION
    client_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    client_name: str = field(default_factory=socket.gethostname)
    nas_shared_folder: str = ""
    auto_receive_enabled: bool = False
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS
    history_display_count: int = DEFAULT_HISTORY_DISPLAY_COUNT
    max_retained_items: int = DEFAULT_MAX_RETAINED_ITEMS
    max_retained_total_bytes: int = DEFAULT_MAX_RETAINED_TOTAL_BYTES
    start_on_login: bool = False
    log_level: str = DEFAULT_LOG_LEVEL

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False, sort_keys=True)


def _coerce(raw: dict[str, Any]) -> Settings:
    """Build a valid Settings from a possibly incomplete/invalid raw dict.

    Unknown or out-of-range values fall back to defaults rather than raising,
    so a hand-edited or partially upgraded config.json never blocks startup.
    """
    defaults = Settings()

    poll_interval = raw.get("poll_interval_seconds", defaults.poll_interval_seconds)
    if poll_interval not in POLL_INTERVAL_CHOICES:
        logger.warning(
            "Ignoring invalid poll_interval_seconds=%r; falling back to %.1f",
            poll_interval,
            DEFAULT_POLL_INTERVAL_SECONDS,
        )
        poll_interval = DEFAULT_POLL_INTERVAL_SECONDS

    history_display_count = raw.get("history_display_count", defaults.history_display_count)
    if not isinstance(history_display_count, int) or history_display_count <= 0:
        history_display_count = defaults.history_display_count

    max_retained_items = raw.get("max_retained_items", defaults.max_retained_items)
    if not isinstance(max_retained_items, int) or max_retained_items <= 0:
        max_retained_items = defaults.max_retained_items

    max_retained_total_bytes = raw.get("max_retained_total_bytes", defaults.max_retained_total_bytes)
    if not isinstance(max_retained_total_bytes, int) or max_retained_total_bytes <= 0:
        max_retained_total_bytes = defaults.max_retained_total_bytes

    return Settings(
        schema_version=SCHEMA_VERSION,
        client_id=raw.get("client_id") or defaults.client_id,
        client_name=raw.get("client_name") or defaults.client_name,
        nas_shared_folder=raw.get("nas_shared_folder", defaults.nas_shared_folder),
        auto_receive_enabled=bool(raw.get("auto_receive_enabled", defaults.auto_receive_enabled)),
        poll_interval_seconds=poll_interval,
        history_display_count=history_display_count,
        max_retained_items=max_retained_items,
        max_retained_total_bytes=max_retained_total_bytes,
        start_on_login=bool(raw.get("start_on_login", defaults.start_on_login)),
        log_level=raw.get("log_level") or defaults.log_level,
    )


def load_settings(path: Path) -> Settings:
    """Load settings from ``path``, creating/repairing the file as needed.

    - Missing file: create one with defaults.
    - Unreadable/malformed file: back it up next to itself and fall back to
      defaults, rather than crashing the app on startup.
    - Valid but partial/out-of-range file: fill in and correct fields.

    The (possibly newly created or corrected) settings are always persisted
    back to ``path`` so the on-disk file stays normalized.
    """
    if not path.exists():
        logger.info("No settings file at %s; creating defaults", path)
        settings = Settings()
        save_settings(path, settings)
        return settings

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError("settings file does not contain a JSON object")
    except (OSError, ValueError, TypeError, UnicodeDecodeError) as exc:
        backup_path = path.with_suffix(f".corrupt-{datetime.now(UTC):%Y%m%dT%H%M%S}.json")
        logger.warning(
            "Failed to read settings from %s (%s); backing up to %s and using defaults",
            path,
            exc,
            backup_path,
        )
        try:
            path.replace(backup_path)
        except OSError:
            logger.exception("Failed to back up corrupt settings file %s", path)
        settings = Settings()
        save_settings(path, settings)
        return settings

    settings = _coerce(raw)
    save_settings(path, settings)
    return settings


def save_settings(path: Path, settings: Settings) -> None:
    atomic_write_text(path, settings.to_json())
