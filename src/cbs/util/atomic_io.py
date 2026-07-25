"""Atomic file write helpers.

Used by local config storage (Phase 0) and the NAS storage backend
(Phase 1) to satisfy the "atomic writes to avoid reading incomplete
files" rule in CLAUDE.md.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _write_via_temp(tmp_dir: Path, final_path: Path, data: bytes, *, prefix: str) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=tmp_dir, prefix=prefix, suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(data)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, final_path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def atomic_write_bytes(path: Path, data: bytes) -> None:
    _write_via_temp(path.parent, path, data, prefix=f".{path.name}.")


def stage_then_move(tmp_dir: Path, final_path: Path, data: bytes, *, stem: str) -> None:
    """Write data to a temp file under tmp_dir, then atomically move it to final_path.

    Unlike atomic_write_bytes (which stages next to its target), this stages
    in a caller-specified directory. Used for the NAS object write protocol,
    where staging must happen under the shared temp/ directory rather than
    directly inside objects/ (docs/design/requirements_review_v0.1.md, 3.3).
    """
    _write_via_temp(tmp_dir, final_path, data, prefix=f"{stem}.")
