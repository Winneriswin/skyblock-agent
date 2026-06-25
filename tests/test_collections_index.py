"""Tests for collections catalog parsing."""

from __future__ import annotations

from skyblock_agent.storage.collections_index import parse_collections_resource


def test_parse_collections_resource_maps_cocoa_and_lotus():
    payload = {
        "collections": {
            "FARMING": {
                "name": "Farming",
                "items": {
                    "INK_SACK:3": {"name": "Cocoa Beans", "maxTiers": 9, "tiers": []},
                    "LEATHER": {"name": "Leather", "maxTiers": 10, "tiers": []},
                    "WHEAT": {"name": "Wheat", "maxTiers": 9, "tiers": []},
                },
            },
            "FISHING": {
                "name": "Fishing",
                "items": {
                    "LOTUS": {"name": "Lotus", "maxTiers": 9, "tiers": []},
                    "INK_SACK": {"name": "Ink Sac", "maxTiers": 9, "tiers": []},
                },
            },
            "COMBAT": {
                "name": "Combat",
                "items": {
                    "SULPHUR": {"name": "Gunpowder", "maxTiers": 9, "tiers": []},
                },
            },
            "MINING": {
                "name": "Mining",
                "items": {
                    "SULPHUR_ORE": {"name": "Sulphur", "maxTiers": 9, "tiers": []},
                },
            },
        }
    }

    catalog = parse_collections_resource(payload)
    items = catalog["items"]
    assert items["INK_SACK:3"]["category"] == "farming"
    assert items["LOTUS"]["category"] == "fishing"
    assert items["SULPHUR"]["category"] == "combat"
    assert items["SULPHUR_ORE"]["category"] == "mining"
    assert items["ENCHANTED_LEATHER"]["category"] == "farming"
