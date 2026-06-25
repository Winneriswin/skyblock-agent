"""Tests for Catacombs parsing and leveling."""

from __future__ import annotations

import json
from pathlib import Path

from skyblock_agent.parsers.dungeon_leveling import dungeon_level_from_experience
from skyblock_agent.parsers.member_dungeons import parse_member_dungeons
from skyblock_agent.storage.collections_index import classify_collection_item, ensure_catalog


def test_dungeon_level_from_experience_basic():
    assert dungeon_level_from_experience(0) == 0.0
    assert dungeon_level_from_experience(25) == 0.5
    assert dungeon_level_from_experience(50) == 1.0
    assert dungeon_level_from_experience(125) == 2.0


def test_lotus_is_fishing_collection():
    ensure_catalog()
    assert classify_collection_item("LOTUS") == "fishing"


def test_parse_member_dungeons_from_cached_profile():
    raw = json.loads(
        Path("data/raw/hypixel_api/profiles/28667672039044989b0019b14a2c34d6.json").read_text(encoding="utf-8")
    )
    profile = next(p for p in raw["data"]["profiles"] if p.get("cute_name") == "Apple")
    member = next(m for m in profile["members"].values() if isinstance(m.get("dungeons"), dict))
    summary = parse_member_dungeons(member)

    assert summary.available is True
    assert summary.level is not None and summary.level >= 50
    assert summary.selected_class == "mage"
    assert len(summary.classes) == 5
    assert any(entry.id == "mage" and entry.selected for entry in summary.classes)

    normal = next(mode for mode in summary.modes if mode.mode == "normal")
    master = next(mode for mode in summary.modes if mode.mode == "master")
    assert any(floor.label == "F7" and floor.completions > 0 for floor in normal.floors)
    assert any(floor.label == "M7" and floor.completions > 0 for floor in master.floors)
    f7 = next(floor for floor in normal.floors if floor.label == "F7")
    assert f7.pb_s_plus_ms == 223562.0
