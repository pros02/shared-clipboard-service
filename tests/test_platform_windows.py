"""Windows start-on-login registry adapter tests.

Exercises the real HKEY_CURRENT_USER Run key (a per-user, non-admin
registry location), always cleaning up afterward so the test doesn't
leave a stray autostart entry behind.
"""
from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="winreg is Windows-only")


@pytest.fixture(autouse=True)
def _cleanup_registry_value():
    from cbs.platform import _windows

    yield
    _windows.disable_start_on_login()


def test_enable_then_is_enabled_then_disable() -> None:
    from cbs.platform import _windows

    assert _windows.is_start_on_login_enabled() is False

    _windows.enable_start_on_login(["C:\\fake\\python.exe", "-m", "cbs"])
    assert _windows.is_start_on_login_enabled() is True

    _windows.disable_start_on_login()
    assert _windows.is_start_on_login_enabled() is False


def test_disable_when_not_enabled_does_not_raise() -> None:
    from cbs.platform import _windows

    _windows.disable_start_on_login()
    _windows.disable_start_on_login()  # calling twice should be harmless


def test_enable_stores_correctly_quoted_command_line() -> None:
    import winreg

    from cbs.platform import _windows

    _windows.enable_start_on_login(["C:\\path with spaces\\python.exe", "-m", "cbs"])

    with winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, _windows._RUN_KEY_PATH) as key:
        value, _ = winreg.QueryValueEx(key, _windows._RUN_VALUE_NAME)

    assert value == '"C:\\path with spaces\\python.exe" -m cbs'
