"""Tests for vanilla icon path resolution."""

from pathlib import Path

from skyblock_agent.collectors.icon_client import PNG_MAGIC
from skyblock_agent.storage import icon_index, item_index


def test_vanilla_icon_filename():
    assert icon_index.vanilla_icon_filename("DIAMOND_SWORD") == "diamond_sword.png"
    assert icon_index.vanilla_icon_filename("minecraft:iron_sword") == "iron_sword.png"


def test_get_vanilla_icon_path_for_item(tmp_path, monkeypatch):
    icon_index.ICONS_DIR = tmp_path / "icons"
    icon_index.VANILLA_ICONS_DIR = icon_index.ICONS_DIR / "vanilla"
    icon_index.META_PATH = icon_index.ICONS_DIR / "meta.json"
    icon_index.MANIFEST_PATH = icon_index.ICONS_DIR / "manifest.json"

    item_index.ITEMS_DIR = tmp_path / "processed" / "items"
    item_index.CATALOG_PATH = item_index.ITEMS_DIR / "catalog.json"
    item_index.META_PATH = item_index.ITEMS_DIR / "meta.json"
    item_index.ITEMS_DIR.mkdir(parents=True)
    item_index.CATALOG_PATH.write_text(
        __import__("json").dumps(
            {
                "items": {
                    "HYPERION": {
                        "id": "HYPERION",
                        "name": "Hyperion",
                        "material": "IRON_SWORD",
                    }
                },
                "categories": {},
            }
        ),
        encoding="utf-8",
    )

    icon_index.VANILLA_ICONS_DIR.mkdir(parents=True)
    png = icon_index.VANILLA_ICONS_DIR / "iron_sword.png"
    png.write_bytes(PNG_MAGIC + b"vanilla-icon-padding" * 4)

    path = icon_index.get_vanilla_icon_path_for_item("HYPERION")
    assert path == png


def test_ensure_vanilla_icon_for_item_downloads(tmp_path, monkeypatch):
    icon_index.ICONS_DIR = tmp_path / "icons"
    icon_index.VANILLA_ICONS_DIR = icon_index.ICONS_DIR / "vanilla"
    icon_index.META_PATH = icon_index.ICONS_DIR / "meta.json"
    icon_index.MANIFEST_PATH = icon_index.ICONS_DIR / "manifest.json"

    item_index.ITEMS_DIR = tmp_path / "processed" / "items"
    item_index.CATALOG_PATH = item_index.ITEMS_DIR / "catalog.json"
    item_index.META_PATH = item_index.ITEMS_DIR / "meta.json"
    item_index.ITEMS_DIR.mkdir(parents=True)
    item_index.CATALOG_PATH.write_text(
        __import__("json").dumps(
            {
                "items": {
                    "ENCHANTED_DIAMOND": {
                        "id": "ENCHANTED_DIAMOND",
                        "name": "Enchanted Diamond",
                        "material": "DIAMOND",
                    }
                },
                "categories": {},
            }
        ),
        encoding="utf-8",
    )

    class FakeClient:
        def fetch_vanilla_icon(self, material: str):
            from skyblock_agent.collectors.icon_client import IconFetchResult, IconSource

            assert material == "DIAMOND"
            return IconFetchResult(
                item_id="DIAMOND",
                data=PNG_MAGIC + b"downloaded-vanilla" * 4,
                source=IconSource.VANILLA_ITEM,
                source_url="https://example.test/diamond.png",
            )

    path = icon_index.ensure_vanilla_icon_for_item("ENCHANTED_DIAMOND", FakeClient())
    assert path is not None
    assert path.is_file()
    assert path.name == "diamond.png"
