"""Local SkyBlock item catalog (imported from Hypixel resources, not fetched by GUI)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skyblock_agent.config import DATA_DIR
from skyblock_agent.models.items import SkyblockItem, item_to_dict

ITEMS_DIR = DATA_DIR / "processed" / "items"
META_PATH = ITEMS_DIR / "meta.json"
CATALOG_PATH = ITEMS_DIR / "catalog.json"

_catalog_cache: dict[str, dict[str, Any]] | None = None
_catalog_mtime: float | None = None


@dataclass
class ItemsCatalogMeta:
    last_imported_at: str
    last_updated: int
    item_count: int
    category_count: int
    raw_path: str
    categories: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_imported_at": self.last_imported_at,
            "last_updated": self.last_updated,
            "item_count": self.item_count,
            "category_count": self.category_count,
            "raw_path": self.raw_path,
            "categories": self.categories,
        }


def catalog_is_available() -> bool:
    return META_PATH.exists() and CATALOG_PATH.exists()


def get_catalog_meta() -> ItemsCatalogMeta | None:
    if not META_PATH.exists():
        return None
    data = json.loads(META_PATH.read_text(encoding="utf-8"))
    return ItemsCatalogMeta(
        last_imported_at=str(data.get("last_imported_at", "")),
        last_updated=int(data.get("last_updated") or 0),
        item_count=int(data.get("item_count") or 0),
        category_count=int(data.get("category_count") or 0),
        raw_path=str(data.get("raw_path", "")),
        categories=list(data.get("categories") or []),
    )


def save_catalog(
    *,
    items: list[SkyblockItem],
    categories: dict[str, list[str]],
    last_imported_at: str,
    last_updated: int,
    raw_path: Path,
) -> tuple[Path, Path]:
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)

    catalog = {
        "items": {item.id: item_to_dict(item) for item in items},
        "categories": categories,
    }
    CATALOG_PATH.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    meta = ItemsCatalogMeta(
        last_imported_at=last_imported_at,
        last_updated=last_updated,
        item_count=len(items),
        category_count=len(categories),
        raw_path=str(raw_path),
        categories=sorted(categories.keys()),
    )
    META_PATH.write_text(
        json.dumps(meta.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return CATALOG_PATH, META_PATH


def load_catalog_items() -> dict[str, dict[str, Any]]:
    global _catalog_cache, _catalog_mtime
    if not CATALOG_PATH.exists():
        return {}
    mtime = CATALOG_PATH.stat().st_mtime
    if _catalog_cache is not None and _catalog_mtime == mtime:
        return _catalog_cache

    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, dict):
        items = {}
    _catalog_cache = items
    _catalog_mtime = mtime
    return items


def get_catalog_item(item_id: str) -> dict[str, Any] | None:
    item = load_catalog_items().get(item_id)
    return item if isinstance(item, dict) else None


def search_items(
    query: str = "",
    *,
    category: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    if not catalog_is_available():
        return []

    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    items_map = data.get("items")
    if not isinstance(items_map, dict):
        return []

    needle = query.strip().lower()
    category_key = category.strip().upper() if category else None

    results: list[dict[str, Any]] = []
    for item in items_map.values():
        if not isinstance(item, dict):
            continue
        if category_key and (item.get("category") or "UNKNOWN") != category_key:
            continue
        if needle:
            haystack = " ".join(
                [
                    str(item.get("id") or ""),
                    str(item.get("name") or ""),
                ]
            ).lower()
            if needle not in haystack and needle.replace(" ", "_") not in haystack:
                continue
        results.append(item)
        if len(results) >= limit:
            break

    results.sort(key=lambda row: str(row.get("name") or row.get("id") or ""))
    return results
