"""Domain concepts shared across layers (storage, clipboard, app).

Kept minimal and free of I/O so any layer can import it without creating
a dependency in the wrong direction.
"""
from __future__ import annotations

from enum import Enum


class ItemType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
