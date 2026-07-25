"""Application entry point: `python -m cbs` (also used by the `cbs` console script)."""
from __future__ import annotations

import sys

from cbs.gui.app import main as _run_gui


def main() -> int:
    return _run_gui()


if __name__ == "__main__":
    sys.exit(main())
