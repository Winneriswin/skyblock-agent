"""Tests for tooltip merge/index helpers."""

import json
from pathlib import Path

from skyblock_agent.storage.tooltips_index import (
    build_name_to_id_map,
    normalize_lookup_name,
    save_tooltips,
    tooltips_are_available,
)


def test_normalize_lookup_name():
    assert normalize_lookup_name("&6Hyperion") == "hyperion"
    assert normalize_lookup_name("§aEnchanted Diamond") == "enchanted diamond"


def test_save_and_load_tooltips(tmp_path, monkeypatch):
    from skyblock_agent.storage import tooltips_index

    tooltips_index.ITEMS_DIR = tmp_path
    tooltips_index.TOOLTIPS_PATH = tmp_path / "tooltips.json"
    tooltips_index.TOOLTIPS_META_PATH = tmp_path / "tooltips_meta.json"

    items = {
        "HYPERION": {
            "item_id": "HYPERION",
            "title": "&6Hyperion",
            "text": "&7Damage: &c+260",
            "lore": ["§7Damage: §c+260"],
            "source": "neu",
        }
    }
    save_tooltips(items=items, sources={"neu": 1}, raw_paths={"neu_items_dir": "/tmp/items"})

    assert tooltips_are_available()
    loaded = json.loads((tmp_path / "tooltips.json").read_text(encoding="utf-8"))
    assert loaded["items"]["HYPERION"]["source"] == "neu"

    mapping = build_name_to_id_map(items)
    assert mapping[normalize_lookup_name("Hyperion")] == "HYPERION"
