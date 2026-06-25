"""Local SkyBlock collections catalog (Hypixel resources API)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skyblock_agent.config import DATA_DIR

COLLECTIONS_DIR = DATA_DIR / "processed" / "collections"
CATALOG_PATH = COLLECTIONS_DIR / "catalog.json"
META_PATH = COLLECTIONS_DIR / "meta.json"

# Profile keys that are not standalone collections but track progress for a parent collection.
COMPANION_ALIASES: dict[str, str] = {
    "ENCHANTED_LEATHER": "LEATHER",
    "RAW_BEEF": "LEATHER",
    "ENCHANTED_RAW_BEEF": "LEATHER",
    "WOOL": "MUTTON",
    "ENCHANTED_MELON": "MELON",
    "ENCHANTED_MELON_BLOCK": "MELON",
    "ENCHANTED_SEEDS": "SEEDS",
    "ENCHANTED_BREAD": "WHEAT",
    "POISONOUS_POTATO": "POTATO_ITEM",
    "RABBIT_FOOT": "RABBIT",
    "RABBIT_HIDE": "RABBIT",
    "ENCHANTED_RABBIT": "RABBIT",
    "ENCHANTED_RABBIT_FOOT": "RABBIT",
    "ENCHANTED_RABBIT_HIDE": "RABBIT",
    "GOLD_ORE": "GOLD_INGOT",
    "ENCHANTED_DIAMOND": "DIAMOND",
    "SNOW_BALL": "ICE",
    "ENCHANTED_ICE": "ICE",
    "ENCHANTED_SNOW_BLOCK": "ICE",
    "ENCHANTED_RAW_FISH": "RAW_FISH",
    "ENCHANTED_RAW_SALMON": "RAW_FISH:1",
    "ENCHANTED_CLOWNFISH": "RAW_FISH:2",
    "ENCHANTED_PUFFERFISH": "RAW_FISH:3",
    "ENCHANTED_PRISMARINE_CRYSTALS": "PRISMARINE_CRYSTALS",
    "ENCHANTED_PRISMARINE_SHARD": "PRISMARINE_SHARD",
    "ENCHANTED_SPONGE": "SPONGE",
}

CATEGORY_ORDER: tuple[str, ...] = (
    "farming",
    "mining",
    "combat",
    "foraging",
    "fishing",
    "rift",
    "boss",
    "other",
)

CATEGORY_LABELS: dict[str, str] = {
    "farming": "Farming",
    "mining": "Mining",
    "combat": "Combat",
    "foraging": "Foraging",
    "fishing": "Fishing",
    "rift": "Rift",
    "boss": "Boss",
    "other": "Other",
}

_catalog_cache: dict[str, Any] | None = None
_catalog_mtime: float | None = None


@dataclass
class CollectionsCatalogMeta:
    last_imported_at: str
    last_updated: int
    collection_count: int
    category_count: int
    raw_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_imported_at": self.last_imported_at,
            "last_updated": self.last_updated,
            "collection_count": self.collection_count,
            "category_count": self.category_count,
            "raw_path": self.raw_path,
        }


def catalog_is_available() -> bool:
    return CATALOG_PATH.exists() and META_PATH.exists()


def get_catalog_meta() -> CollectionsCatalogMeta | None:
    if not META_PATH.exists():
        return None
    data = json.loads(META_PATH.read_text(encoding="utf-8"))
    return CollectionsCatalogMeta(
        last_imported_at=str(data.get("last_imported_at", "")),
        last_updated=int(data.get("last_updated") or 0),
        collection_count=int(data.get("collection_count") or 0),
        category_count=int(data.get("category_count") or 0),
        raw_path=str(data.get("raw_path", "")),
    )


def save_catalog(*, catalog: dict[str, Any], last_updated: int, raw_path: Path) -> tuple[Path, Path]:
    COLLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    imported_at = datetime.now(timezone.utc).isoformat()
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    meta = {
        "last_imported_at": imported_at,
        "last_updated": last_updated,
        "collection_count": len(catalog.get("items") or {}),
        "category_count": len(catalog.get("categories") or {}),
        "raw_path": str(raw_path),
    }
    META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    global _catalog_cache, _catalog_mtime
    _catalog_cache = catalog
    _catalog_mtime = CATALOG_PATH.stat().st_mtime
    return CATALOG_PATH, META_PATH


def parse_collections_resource(payload: dict[str, Any]) -> dict[str, Any]:
    root = payload.get("collections")
    if not isinstance(root, dict):
        return {"items": {}, "categories": {}}

    items: dict[str, dict[str, Any]] = {}
    categories: dict[str, dict[str, Any]] = {}

    for category_id, category in root.items():
        if not isinstance(category, dict):
            continue
        category_key = str(category_id).lower()
        category_items = category.get("items")
        if not isinstance(category_items, dict):
            continue

        ordered_ids: list[str] = []
        for sort_index, (item_id, item) in enumerate(category_items.items()):
            key = str(item_id).strip().upper()
            ordered_ids.append(key)
            items[key] = {
                "item_id": key,
                "name": str((item or {}).get("name") or key.replace("_", " ").title()),
                "category": category_key,
                "sort_index": sort_index,
                "official": True,
            }

        categories[category_key] = {
            "id": category_key,
            "label": str(category.get("name") or CATEGORY_LABELS.get(category_key, category_key.title())),
            "item_ids": ordered_ids,
        }

    for alias, parent_id in COMPANION_ALIASES.items():
        alias_key = alias.strip().upper()
        parent_key = parent_id.strip().upper()
        parent = items.get(parent_key)
        if parent is None:
            continue
        items[alias_key] = {
            "item_id": alias_key,
            "name": alias_key.replace("_", " ").title(),
            "category": parent["category"],
            "sort_index": parent["sort_index"],
            "official": False,
            "parent_item_id": parent_key,
        }

    return {"items": items, "categories": categories}


def load_catalog() -> dict[str, Any]:
    global _catalog_cache, _catalog_mtime
    if not CATALOG_PATH.exists():
        return {"items": {}, "categories": {}}

    mtime = CATALOG_PATH.stat().st_mtime
    if _catalog_cache is not None and _catalog_mtime == mtime:
        return _catalog_cache

    _catalog_cache = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    _catalog_mtime = mtime
    return _catalog_cache


def ensure_catalog() -> dict[str, Any]:
    if catalog_is_available():
        return load_catalog()

    from skyblock_agent.collectors.collections_importer import CollectionsImporter

    CollectionsImporter().import_collections(save_raw=True)
    return load_catalog()


def get_collection_entry(item_id: str) -> dict[str, Any] | None:
    key = item_id.strip().upper()
    catalog = ensure_catalog()
    items = catalog.get("items") or {}
    entry = items.get(key)
    return dict(entry) if isinstance(entry, dict) else None


def classify_collection_item(item_id: str) -> str:
    entry = get_collection_entry(item_id)
    if entry and entry.get("category"):
        return str(entry["category"])
    return "other"


def collection_display_name(item_id: str) -> str | None:
    entry = get_collection_entry(item_id)
    if entry and entry.get("name"):
        return str(entry["name"])
    return None


def collection_sort_key(item_id: str) -> tuple[int, int, str]:
    key = item_id.strip().upper()
    entry = get_collection_entry(key)
    if entry:
        category = str(entry.get("category") or "other")
        category_index = CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else len(CATEGORY_ORDER)
        sort_index = int(entry.get("sort_index") or 9999)
        if not entry.get("official"):
            sort_index += 1000
        return (category_index, sort_index, key.lower())
    return (len(CATEGORY_ORDER), 9999, key.lower())
