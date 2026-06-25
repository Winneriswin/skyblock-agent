"""Import SkyBlock collections catalog from Hypixel resources API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from skyblock_agent.collectors.resource_client import ResourceClient
from skyblock_agent.storage.collections_index import CollectionsCatalogMeta, parse_collections_resource, save_catalog
from skyblock_agent.storage.raw_store import save_raw_json


@dataclass
class CollectionsImportResult:
    meta: CollectionsCatalogMeta
    catalog_path: Path
    meta_path: Path


class CollectionsImporter:
    """Download and index v2/resources/skyblock/collections (no API key required)."""

    def __init__(self, resources: ResourceClient | None = None) -> None:
        self.resources = resources or ResourceClient()

    def import_collections(self, *, save_raw: bool = True) -> CollectionsImportResult:
        payload = self.resources.get_skyblock_collections()
        raw_path = Path()
        if save_raw:
            raw_path = save_raw_json("resources", "collections", payload)

        catalog = parse_collections_resource(payload)
        catalog_path, meta_path = save_catalog(
            catalog=catalog,
            last_updated=int(payload.get("lastUpdated") or 0),
            raw_path=raw_path,
        )
        meta = CollectionsCatalogMeta(
            last_imported_at=datetime.now(timezone.utc).isoformat(),
            last_updated=int(payload.get("lastUpdated") or 0),
            collection_count=len(catalog.get("items") or {}),
            category_count=len(catalog.get("categories") or {}),
            raw_path=str(raw_path),
        )
        return CollectionsImportResult(meta=meta, catalog_path=catalog_path, meta_path=meta_path)

    def close(self) -> None:
        self.resources.close()

    def __enter__(self) -> CollectionsImporter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
