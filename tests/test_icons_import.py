"""Tests for item icon import."""

from unittest.mock import MagicMock

from skyblock_agent.collectors.icon_client import IconFetchResult, IconSource, PNG_MAGIC
from skyblock_agent.collectors.icons_importer import IconsImporter
from skyblock_agent.storage.icon_index import (
    get_icon_path,
    has_icon,
    icons_are_available,
    load_manifest,
)

FIXTURE_PNG = PNG_MAGIC + b"test-icon-bytes-padding" * 4


def test_icons_importer_writes_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("SKYBLOCK_AGENT_DATA_DIR", str(tmp_path))

    from skyblock_agent import config

    config.DATA_DIR = tmp_path

    from skyblock_agent.storage import icon_index, item_index

    item_index.ITEMS_DIR = tmp_path / "processed" / "items"
    item_index.META_PATH = item_index.ITEMS_DIR / "meta.json"
    item_index.CATALOG_PATH = item_index.ITEMS_DIR / "catalog.json"
    icon_index.ICONS_DIR = tmp_path / "processed" / "items" / "icons"
    icon_index.META_PATH = icon_index.ICONS_DIR / "meta.json"
    icon_index.MANIFEST_PATH = icon_index.ICONS_DIR / "manifest.json"

    catalog = {
        "items": {
            "ENCHANTED_DIAMOND": {
                "id": "ENCHANTED_DIAMOND",
                "name": "Enchanted Diamond",
                "category": "BLOCK",
                "tier": "UNCOMMON",
                "material": "DIAMOND",
                "npc_sell_price": 320,
            },
            "MISSING_ICON": {
                "id": "MISSING_ICON",
                "name": "Missing",
                "category": "MISC",
                "tier": "COMMON",
                "material": "UNKNOWN_MATERIAL",
                "npc_sell_price": None,
            },
        },
        "categories": {"BLOCK": ["ENCHANTED_DIAMOND"], "MISC": ["MISSING_ICON"]},
    }
    item_index.ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    item_index.CATALOG_PATH.write_text(__import__("json").dumps(catalog), encoding="utf-8")
    item_index.META_PATH.write_text(
        __import__("json").dumps(
            {
                "last_imported_at": "2026-01-01T00:00:00+00:00",
                "last_updated": 0,
                "item_count": 2,
                "category_count": 2,
                "raw_path": "",
                "categories": ["BLOCK", "MISC"],
            }
        ),
        encoding="utf-8",
    )

    client = MagicMock()
    client.fetch_icon.side_effect = lambda item_id, material=None: (
        IconFetchResult(
            item_id=item_id,
            data=FIXTURE_PNG,
            source=IconSource.COFLNET,
            source_url=f"https://example.test/{item_id}",
        )
        if item_id == "ENCHANTED_DIAMOND"
        else None
    )

    with IconsImporter(client=client) as importer:
        result = importer.import_icons(delay_seconds=0.0)

    assert result.meta.downloaded == 1
    assert result.meta.failed == 1
    assert icons_are_available()
    assert has_icon("ENCHANTED_DIAMOND")
    assert not has_icon("MISSING_ICON")

    path = get_icon_path("ENCHANTED_DIAMOND")
    assert path is not None
    assert path.read_bytes().startswith(PNG_MAGIC)

    manifest = load_manifest()
    assert manifest["ENCHANTED_DIAMOND"]["source"] == "coflnet"
