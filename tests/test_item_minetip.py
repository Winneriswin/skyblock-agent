"""Tests for NBT item minetip formatting."""

from skyblock_agent.parsers.item_minetip import minetip_from_item_dict


def test_minetip_from_nbt_lore():
    item = {
        "item_id": "HYPERION",
        "name": "§6§lHyperion",
        "display_name": "Hyperion",
        "lore": [
            "§7Gear Score: §d1200",
            "§7Damage: §c+359",
            "§8HYPERION",
        ],
        "count": 1,
    }
    tip = minetip_from_item_dict(item)
    assert tip["title"] == "&6&lHyperion"
    assert "&7Gear Score: &d1200" in tip["text"]
    assert tip["text"].endswith("&8HYPERION")


def test_minetip_skips_duplicate_title_line():
    item = {
        "item_id": "DIAMOND_SWORD",
        "name": "§fDiamond Sword",
        "lore": ["§fDiamond Sword", "§7Sharpness V"],
        "count": 1,
    }
    tip = minetip_from_item_dict(item)
    assert tip["title"] == "&fDiamond Sword"
    assert "&7Sharpness V" in tip["text"]
    assert tip["text"].count("Diamond Sword") == 0


def test_minetip_fallback_without_lore():
    item = {
        "item_id": "ENCHANTED_DIAMOND",
        "display_name": "Enchanted Diamond",
        "lore": [],
        "count": 64,
    }
    tip = minetip_from_item_dict(item)
    assert "Enchanted Diamond" in tip["title"]
    assert "&7Count: &f64" in tip["text"]
    assert "&8ENCHANTED_DIAMOND" in tip["text"]
