"""Tests for SkyBlock item catalog import."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from skyblock_agent.collectors.items_importer import ItemsImporter
from skyblock_agent.models.items import build_category_index, parse_items
from skyblock_agent.storage.item_index import catalog_is_available, get_catalog_meta, search_items

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_parse_items():
    payload = _load("items_sample.json")
    items = parse_items(payload)
    assert len(items) == 2
    assert items[0].id == "ASPECT_OF_THE_DRAGONS"
    assert items[1].npc_sell_price == 320


def test_build_category_index():
    payload = _load("items_sample.json")
    items = parse_items(payload)
    index = build_category_index(items)
    assert index["SWORD"] == ["ASPECT_OF_THE_DRAGONS"]
    assert index["BLOCK"] == ["ENCHANTED_DIAMOND"]


def test_items_importer_writes_catalog(tmp_path, monkeypatch):
    monkeypatch.setenv("SKYBLOCK_AGENT_DATA_DIR", str(tmp_path))

    from skyblock_agent import config

    config.DATA_DIR = tmp_path
    config.RAW_HYPIXEL_DIR = tmp_path / "raw" / "hypixel_api"

    from skyblock_agent.storage import item_index, raw_store

    item_index.ITEMS_DIR = tmp_path / "processed" / "items"
    item_index.META_PATH = item_index.ITEMS_DIR / "meta.json"
    item_index.CATALOG_PATH = item_index.ITEMS_DIR / "catalog.json"
    raw_store.RAW_HYPIXEL_DIR = tmp_path / "raw" / "hypixel_api"

    resources = MagicMock()
    resources.get_skyblock_items.return_value = _load("items_sample.json")

    with ItemsImporter(resources=resources) as importer:
        result = importer.import_items()

    assert result.meta.item_count == 2
    assert catalog_is_available()
    meta = get_catalog_meta()
    assert meta is not None
    assert meta.item_count == 2

    matches = search_items("diamond")
    assert len(matches) == 1
    assert matches[0]["id"] == "ENCHANTED_DIAMOND"
