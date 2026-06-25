"""Import SkyBlock item tooltips from wiki, NEU, and Hypixel resources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skyblock_agent.collectors.neu_importer import NeuItemsImporter, load_neu_tooltips
from skyblock_agent.collectors.resource_client import ResourceClient
from skyblock_agent.collectors.wiki_client import WikiClient
from skyblock_agent.config import DATA_DIR
from skyblock_agent.models.items import item_to_dict, parse_items
from skyblock_agent.parsers.hypixel_tooltip import build_hypixel_base_tooltip
from skyblock_agent.parsers.wiki_tooltips import parse_wiki_tooltips_module
from skyblock_agent.storage.item_index import load_catalog_items
from skyblock_agent.storage.tooltips_index import (
    build_name_to_id_map,
    normalize_lookup_name,
    save_tooltips,
)

WIKI_TOOLTIPS_MODULE = "Module:Inventory slot/Tooltips"
RAW_WIKI_DIR = DATA_DIR / "raw" / "wiki"
RAW_NEU_DIR = DATA_DIR / "raw" / "neu"


@dataclass
class TooltipsImportResult:
    item_count: int
    sources: dict[str, int]
    tooltips_path: Path
    meta_path: Path


class TooltipsImporter:
    """Download tooltip data locally (manual sync, not on GUI startup)."""

    def __init__(
        self,
        *,
        wiki: WikiClient | None = None,
        neu: NeuItemsImporter | None = None,
        resources: ResourceClient | None = None,
    ) -> None:
        self.wiki = wiki or WikiClient()
        self.neu = neu or NeuItemsImporter()
        self.resources = resources or ResourceClient()
        self._owns_wiki = wiki is None
        self._owns_neu = neu is None
        self._owns_resources = resources is None

    def import_tooltips(
        self,
        *,
        sources: tuple[str, ...] = ("neu", "wiki", "hypixel"),
        save_raw: bool = True,
    ) -> TooltipsImportResult:
        merged: dict[str, dict[str, Any]] = {}
        source_counts: dict[str, int] = {}
        raw_paths: dict[str, str] = {}

        name_to_id = self._build_catalog_name_index()

        if "neu" in sources:
            neu_result = self.neu.import_items(raw_dir=RAW_NEU_DIR, extract=True)
            if save_raw:
                raw_paths["neu_zip"] = str(neu_result.zip_path)
                raw_paths["neu_items_dir"] = str(neu_result.items_dir)
            neu_records = load_neu_tooltips(neu_result.items_dir)
            source_counts["neu"] = self._merge_records(merged, neu_records)
            name_to_id.update(build_name_to_id_map(neu_records))

        if "wiki" in sources:
            module_source = self.wiki.get_module_source(WIKI_TOOLTIPS_MODULE)
            if save_raw:
                wiki_path = RAW_WIKI_DIR / "inventory_slot_tooltips.lua"
                RAW_WIKI_DIR.mkdir(parents=True, exist_ok=True)
                wiki_path.write_text(module_source, encoding="utf-8")
                raw_paths["wiki_tooltips"] = str(wiki_path)

            wiki_records = self._map_wiki_records(
                parse_wiki_tooltips_module(module_source),
                name_to_id,
            )
            source_counts["wiki"] = self._merge_records(merged, wiki_records, overwrite=False)

        if "hypixel" in sources:
            hypixel_records = self._load_hypixel_records()
            source_counts["hypixel"] = self._merge_records(
                merged,
                hypixel_records,
                overwrite=False,
            )

        tooltips_path, meta_path = save_tooltips(
            items=merged,
            sources=source_counts,
            raw_paths=raw_paths,
        )
        return TooltipsImportResult(
            item_count=len(merged),
            sources=source_counts,
            tooltips_path=tooltips_path,
            meta_path=meta_path,
        )

    def _build_catalog_name_index(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for item_id, item in load_catalog_items().items():
            name = str(item.get("name") or "")
            if name:
                mapping[normalize_lookup_name(name)] = item_id
            mapping[normalize_lookup_name(item_id.replace("_", " "))] = item_id
        return mapping

    def _map_wiki_records(
        self,
        wiki_by_name: dict[str, dict[str, Any]],
        name_to_id: dict[str, str],
    ) -> dict[str, dict[str, Any]]:
        mapped: dict[str, dict[str, Any]] = {}
        for display_name, record in wiki_by_name.items():
            item_id = name_to_id.get(normalize_lookup_name(display_name))
            if not item_id:
                alias_name = record.get("name")
                if isinstance(alias_name, str):
                    item_id = name_to_id.get(normalize_lookup_name(alias_name))
            if not item_id:
                continue
            mapped[item_id] = {
                "item_id": item_id,
                "title": record.get("title") or "",
                "text": record.get("text") or "",
                "lore": None,
                "source": "wiki",
            }
        return mapped

    def _load_hypixel_records(self) -> dict[str, dict[str, Any]]:
        catalog = load_catalog_items()
        if catalog and any(isinstance(item, dict) and item.get("stats") for item in catalog.values()):
            raw_items = list(catalog.values())
        else:
            payload = self.resources.get_skyblock_items()
            raw_items = [item_to_dict(item) for item in parse_items(payload)]

        records: dict[str, dict[str, Any]] = {}
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            tooltip = build_hypixel_base_tooltip(item)
            if tooltip:
                records[tooltip["item_id"]] = tooltip
        return records

    @staticmethod
    def _merge_records(
        target: dict[str, dict[str, Any]],
        incoming: dict[str, dict[str, Any]],
        *,
        overwrite: bool = True,
    ) -> int:
        added = 0
        for item_id, record in incoming.items():
            if overwrite or item_id not in target:
                if item_id not in target:
                    added += 1
                target[item_id] = record
        return added

    def close(self) -> None:
        if self._owns_wiki:
            self.wiki.close()
        if self._owns_neu:
            self.neu.close()
        if self._owns_resources:
            self.resources.close()

    def __enter__(self) -> TooltipsImporter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
