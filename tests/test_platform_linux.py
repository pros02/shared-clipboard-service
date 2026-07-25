"""Linux XDG autostart adapter tests.

These test pure path/file logic in cbs.platform._linux, which doesn't
require actually running on Linux — XDG_CONFIG_HOME is redirected to a
temp directory so nothing touches the real user config.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_xdg_config_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


def test_enable_creates_desktop_file_with_exec_line(tmp_path: Path) -> None:
    from cbs.platform import _linux

    _linux.enable_start_on_login(["/usr/bin/python3", "-m", "cbs"])

    desktop_file = tmp_path / "autostart" / "shared-clipboard-service.desktop"
    assert desktop_file.exists()
    content = desktop_file.read_text(encoding="utf-8")
    assert "Exec=/usr/bin/python3 -m cbs" in content
    assert "Type=Application" in content


def test_enable_quotes_arguments_with_spaces(tmp_path: Path) -> None:
    from cbs.platform import _linux

    _linux.enable_start_on_login(["/usr/bin/python3", "-m", "cbs", "--flag", "value with spaces"])

    content = (tmp_path / "autostart" / "shared-clipboard-service.desktop").read_text(encoding="utf-8")
    assert "'value with spaces'" in content


def test_is_enabled_reflects_file_presence() -> None:
    from cbs.platform import _linux

    assert _linux.is_start_on_login_enabled() is False

    _linux.enable_start_on_login(["/usr/bin/python3", "-m", "cbs"])
    assert _linux.is_start_on_login_enabled() is True

    _linux.disable_start_on_login()
    assert _linux.is_start_on_login_enabled() is False


def test_disable_when_not_enabled_does_not_raise() -> None:
    from cbs.platform import _linux

    _linux.disable_start_on_login()
    _linux.disable_start_on_login()
