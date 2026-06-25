"""Parse Hypixel SkyBlock items resource payload."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SkyblockItem:
    id: str
    name: str
    category: str | None
    tier: str | None
    material: str | None
    npc_sell_price: int | None
    stats: dict[str, float] | None = None
    dungeon_item: bool | None = None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_stats(raw: Any) -> dict[str, float] | None:
    if not isinstance(raw, dict):
        return None
    stats: dict[str, float] = {}
    for key, value in raw.items():
        parsed = _optional_float(value)
        if parsed is not None:
            stats[str(key)] = parsed
    return stats or None


def parse_item(raw: dict[str, Any]) -> SkyblockItem | None:
    if not isinstance(raw, dict):
        return None

    item_id = str(raw.get("id") or "").strip()
    if not item_id:
        return None

    category = raw.get("category")
    tier = raw.get("tier")
    material = raw.get("material")

    return SkyblockItem(
        id=item_id,
        name=str(raw.get("name") or item_id),
        category=str(category) if category else None,
        tier=str(tier) if tier else None,
        material=str(material) if material else None,
        npc_sell_price=_optional_int(raw.get("npc_sell_price")),
        stats=_parse_stats(raw.get("stats")),
        dungeon_item=bool(raw.get("dungeon_item")) if raw.get("dungeon_item") is not None else None,
    )


def parse_items(payload: dict[str, Any]) -> list[SkyblockItem]:
    items_root = payload.get("items")
    if not isinstance(items_root, list):
        return []

    items: list[SkyblockItem] = []
    for raw in items_root:
        parsed = parse_item(raw)
        if parsed is not None:
            items.append(parsed)
    items.sort(key=lambda item: item.id)
    return items


def item_to_dict(item: SkyblockItem) -> dict[str, Any]:
    payload = {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "tier": item.tier,
        "material": item.material,
        "npc_sell_price": item.npc_sell_price,
    }
    if item.stats:
        payload["stats"] = item.stats
    if item.dungeon_item is not None:
        payload["dungeon_item"] = item.dungeon_item
    return payload


def build_category_index(items: list[SkyblockItem]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for item in items:
        key = item.category or "UNKNOWN"
        index.setdefault(key, []).append(item.id)
    for category in index:
        index[category].sort()
    return index
