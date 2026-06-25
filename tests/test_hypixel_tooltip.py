"""Tests for Hypixel stats tooltip generation."""

from skyblock_agent.parsers.hypixel_tooltip import build_hypixel_base_tooltip


def test_build_hypixel_base_tooltip():
    tooltip = build_hypixel_base_tooltip(
        {
            "id": "HYPERION",
            "name": "Hyperion",
            "tier": "LEGENDARY",
            "category": "SWORD",
            "stats": {"DAMAGE": 260, "STRENGTH": 150, "INTELLIGENCE": 350},
        }
    )
    assert tooltip is not None
    assert tooltip["title"] == "&6Hyperion"
    assert "Damage" in tooltip["text"]
    assert "Strength" in tooltip["text"]
    assert tooltip["source"] == "hypixel"


def test_build_hypixel_base_tooltip_skips_empty():
    assert build_hypixel_base_tooltip({"id": "ROCK", "name": "Rock"}) is None
