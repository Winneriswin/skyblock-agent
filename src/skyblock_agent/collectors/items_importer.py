"""Import SkyBlock item catalog from Hypixel static resources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from skyblock_agent.collectors.resource_client import ResourceClient
from skyblock_agent.models.items import build_category_index, parse_items
from skyblock_agent.storage.item_index import ItemsCatalogMeta, save_catalog
from skyblock_agent.storage.raw_store import save_raw_json


@dataclass
class ItemsImportResult:
    meta: ItemsCatalogMeta
    catalog_path: Path
    meta_path: Path


class ItemsImporter:
    """Download and index v2/resources/skyblock/items (run manually, not on GUI startup)."""

    def __init__(self, resources: ResourceClient | None = None) -> None:
        self.resources = resources or ResourceClient()

    def import_items(self, *, save_raw: bool = True) -> ItemsImportResult:
        payload = self.resources.get_skyblock_items()
        raw_path = Path()
        if save_raw:
            raw_path = save_raw_json("resources", "items", payload)

        items = parse_items(payload)
        categories = build_category_index(items)
        imported_at = datetime.now(timezone.utc).isoformat()
        catalog_path, meta_path = save_catalog(
            items=items,
            categories=categories,
            last_imported_at=imported_at,
            last_updated=int(payload.get("lastUpdated") or 0),
            raw_path=raw_path,
        )

        meta = ItemsCatalogMeta(
            last_imported_at=imported_at,
            last_updated=int(payload.get("lastUpdated") or 0),
            item_count=len(items),
            category_count=len(categories),
            raw_path=str(raw_path),
            categories=sorted(categories.keys()),
        )
        return ItemsImportResult(meta=meta, catalog_path=catalog_path, meta_path=meta_path)

    def close(self) -> None:
        self.resources.close()

    def __enter__(self) -> ItemsImporter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
