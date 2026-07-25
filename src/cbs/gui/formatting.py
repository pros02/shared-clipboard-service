"""Small display-formatting helpers shared across GUI widgets."""
from __future__ import annotations

from cbs.domain import ItemType

_TYPE_LABELS: dict[ItemType, str] = {
    ItemType.TEXT: "テキスト",
    ItemType.IMAGE: "画像",
    ItemType.FILE: "ファイル",
}


def type_label(item_type: ItemType) -> str:
    return _TYPE_LABELS.get(item_type, item_type.value)
