"""Fixed per-type size limits for outgoing clipboard items.

Decided in docs/design/requirements_review_v0.1.md, section 3.5. These
are fixed application constants, not user-configurable settings.
"""
from __future__ import annotations

from cbs.domain import ItemType

TEXT_MAX_BYTES = 2 * 1024 * 1024
IMAGE_MAX_BYTES = 50 * 1024 * 1024
FILE_MAX_BYTES = 500 * 1024 * 1024

_LIMITS_BY_TYPE = {
    ItemType.TEXT: TEXT_MAX_BYTES,
    ItemType.IMAGE: IMAGE_MAX_BYTES,
    ItemType.FILE: FILE_MAX_BYTES,
}


def limit_for(item_type: ItemType) -> int:
    return _LIMITS_BY_TYPE[item_type]
