"""Manual clipboard smoke test.

Automated tests (tests/test_clipboard_qt_adapter.py) already verify that
QtClipboardAdapter can round-trip text/image/file content it wrote itself.
What they can't verify is interop with *other* real applications on this
OS (Explorer, Nautilus, image viewers, etc.) — that needs a human.

Run this on the target machine's actual desktop session (not a headless
SSH session) and follow the prompts:

    python scripts/clipboard_smoke_test.py
"""
from __future__ import annotations

import os

from cbs.clipboard.models import ClipboardContent
from cbs.clipboard.qt_adapter import QtClipboardAdapter
from cbs.domain import ItemType


def _describe(content: ClipboardContent | None) -> str:
    if content is None:
        return "(nothing detected / empty or unsupported clipboard content)"
    if content.type is ItemType.TEXT:
        return f"TEXT: {content.text!r}"
    if content.type is ItemType.IMAGE:
        size = len(content.image_png) if content.image_png else 0
        return f"IMAGE: {size} bytes of PNG data"
    return "FILES: " + ", ".join(str(p) for p in content.file_paths)


def main() -> None:
    adapter = QtClipboardAdapter()

    print("=== Clipboard smoke test ===")
    print(f"XDG_SESSION_TYPE={os.environ.get('XDG_SESSION_TYPE', '(not set, likely Windows)')}")
    print()

    input("1) Copy some plain TEXT in another app, then press Enter here...")
    print("   Detected:", _describe(adapter.read()))
    print()

    input(
        "2) Copy an IMAGE in another app (e.g. a screenshot tool or image "
        "viewer's 'copy image'), then press Enter here..."
    )
    print("   Detected:", _describe(adapter.read()))
    print()

    input(
        "3) Copy one or more FILES in your file manager (Explorer / "
        "Nautilus), then press Enter here..."
    )
    print("   Detected:", _describe(adapter.read()))
    print()

    print("Now testing this app writing TO the clipboard:")
    adapter.write(ClipboardContent.from_text("shared-clipboard-service smoke test"))
    input("   Wrote text to the clipboard — paste it somewhere to confirm, then press Enter...")

    print("Done.")


if __name__ == "__main__":
    main()
