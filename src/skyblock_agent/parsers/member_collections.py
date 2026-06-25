"""Parse SkyBlock collection progress from a profile member payload."""

from __future__ import annotations

from typing import Any

from skyblock_agent.models.inventory import CollectionEntry, CollectionGroup, CollectionsSummary
from skyblock_agent.storage.collections_index import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    classify_collection_item,
    collection_display_name,
    collection_sort_key,
)
from skyblock_agent.storage.item_index import get_catalog_item


def _display_name(item_id: str) -> str:
    official = collection_display_name(item_id)
    if official:
        return official

    key = item_id.strip().upper()
    catalog = get_catalog_item(key)
    if catalog and catalog.get("name"):
        return str(catalog["name"])
    return key.replace("_", " ").title()


def _build_groups(entries: list[CollectionEntry]) -> list[CollectionGroup]:
    by_type: dict[str, list[CollectionEntry]] = {category: [] for category in CATEGORY_ORDER}
    for entry in entries:
        by_type.setdefault(entry.collection_type, []).append(entry)

    groups: list[CollectionGroup] = []
    for category_id in CATEGORY_ORDER:
        category_entries = by_type.get(category_id) or []
        if not category_entries:
            continue
        groups.append(
            CollectionGroup(
                id=category_id,
                label=CATEGORY_LABELS[category_id],
                entry_count=len(category_entries),
                total_amount=sum(entry.amount for entry in category_entries),
                entries=category_entries,
            )
        )
    return groups


def parse_member_collections(member: dict[str, Any]) -> CollectionsSummary:
    raw = member.get("collection")
    if not isinstance(raw, dict) or not raw:
        return CollectionsSummary()

    entries: list[CollectionEntry] = []
    for item_id, amount in raw.items():
        if not isinstance(item_id, str):
            continue
        try:
            count = int(amount)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue

        key = item_id.strip().upper()
        entries.append(
            CollectionEntry(
                item_id=key,
                display_name=_display_name(key),
                amount=count,
                collection_type=classify_collection_item(key),
            )
        )

    entries.sort(key=lambda entry: collection_sort_key(entry.item_id))
    total_items = sum(entry.amount for entry in entries)
    return CollectionsSummary(entries=entries, total_items=total_items, groups=_build_groups(entries))
