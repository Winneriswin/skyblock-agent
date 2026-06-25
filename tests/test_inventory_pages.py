"""Tests for inventory page splitting and storage parsing."""

import json
from pathlib import Path

from skyblock_agent.parsers.inventory_pages import (
    ACCESSORY_BAG_TIERS,
    BACKPACK_SIZES,
    EC_CAPACITY_TIERS,
    build_accessory_bag_pages,
    build_backpack_page,
    build_ender_chest_pages,
    build_wardrobe_page,
    build_wardrobe_pages_from_blob,
    classify_storage_key,
    extract_wardrobe_set_items,
    infer_accessory_bag_capacity,
    infer_backpack_size,
    infer_ender_chest_capacity,
    parse_storage_key_index,
    split_fixed_pages,
)
from skyblock_agent.models.inventory import ItemStack
from skyblock_agent.parsers.collection_categories import classify_collection_item
from skyblock_agent.parsers.member_collections import parse_member_collections
from skyblock_agent.parsers.member_inventories import CONTAINER_ORDER, parse_member_inventories

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _stack(slot: int, item_id: str) -> ItemStack:
    return ItemStack(
        slot=slot,
        item_id=item_id,
        name=f"§a{item_id}",
        display_name=item_id.replace("_", " "),
    )


def test_classify_storage_key():
    assert classify_storage_key("0") == "backpack"
    assert classify_storage_key("17") == "backpack"
    assert classify_storage_key("wd0") == "wardrobe"
    assert classify_storage_key("WD3") == "wardrobe"
    assert classify_storage_key("other") == "unknown"


def test_parse_storage_key_index():
    assert parse_storage_key_index("wd2", fallback=0) == 2
    assert parse_storage_key_index("5", fallback=0) == 5


def test_infer_ender_chest_capacity():
    assert infer_ender_chest_capacity(-1) == EC_CAPACITY_TIERS[0]
    assert infer_ender_chest_capacity(53) == 54
    assert infer_ender_chest_capacity(404) == 405


def test_infer_backpack_size():
    assert infer_backpack_size(8) == 9
    assert infer_backpack_size(44) == 45


def test_infer_accessory_bag_capacity():
    assert infer_accessory_bag_capacity(-1) == ACCESSORY_BAG_TIERS[0]
    assert infer_accessory_bag_capacity(2) == 3
    assert infer_accessory_bag_capacity(56) == 57
    assert infer_accessory_bag_capacity(100) == 135


def test_build_accessory_bag_pages():
    stacks = [_stack(46, "ROCK")]
    pages = build_accessory_bag_pages(stacks)
    assert len(pages) >= 2
    assert pages[1].items[0].slot == 1


def test_build_wardrobe_page_column_layout():
    stacks = [
        _stack(0, "MINERAL_HELMET"),
        _stack(9, "MINERAL_CHESTPLATE"),
        _stack(18, "MINERAL_LEGGINGS"),
        _stack(27, "MINERAL_BOOTS"),
    ]
    page = build_wardrobe_page(index=0, stacks=stacks)
    assert page.slot_count == 4
    assert len(page.items) == 4
    assert [item.item_id for item in page.items] == [
        "MINERAL_HELMET",
        "MINERAL_CHESTPLATE",
        "MINERAL_LEGGINGS",
        "MINERAL_BOOTS",
    ]


def test_build_wardrobe_page_linear_fallback():
    stacks = [_stack(2, "HYPERION")]
    page = build_wardrobe_page(index=0, stacks=stacks)
    assert page.items[0].slot == 2


def test_wardrobe_column_layout_detection():
    linear = [_stack(0, "A"), _stack(1, "B"), _stack(2, "C"), _stack(3, "D")]
    column = [_stack(0, "A"), _stack(9, "B"), _stack(18, "C"), _stack(27, "D")]
    linear_multi = [_stack(i, f"ITEM_{i}") for i in range(12)]
    from skyblock_agent.parsers.inventory_pages import _wardrobe_uses_column_layout

    assert _wardrobe_uses_column_layout(linear) is False
    assert _wardrobe_uses_column_layout(column) is True
    assert _wardrobe_uses_column_layout(linear_multi) is False


def test_build_wardrobe_pages_linear_blob():
    stacks = [
        _stack(0, "A_HELMET"),
        _stack(1, "A_CHESTPLATE"),
        _stack(2, "A_LEGGINGS"),
        _stack(3, "A_BOOTS"),
        _stack(4, "B_HELMET"),
        _stack(5, "B_CHESTPLATE"),
        _stack(6, "B_LEGGINGS"),
        _stack(7, "B_BOOTS"),
    ]
    pages = build_wardrobe_pages_from_blob(stacks)
    assert len(pages) == 2
    assert pages[0].items[0].item_id == "A_HELMET"
    assert pages[1].items[3].item_id == "B_BOOTS"


def test_build_wardrobe_pages_from_single_blob():
    stacks = [
        _stack(0, "A_HELMET"),
        _stack(9, "A_CHESTPLATE"),
        _stack(18, "A_LEGGINGS"),
        _stack(27, "A_BOOTS"),
        _stack(1, "B_HELMET"),
        _stack(10, "B_CHESTPLATE"),
        _stack(19, "B_LEGGINGS"),
        _stack(28, "B_BOOTS"),
    ]
    pages = build_wardrobe_pages_from_blob(stacks)
    assert len(pages) == 2
    assert pages[0].items[0].item_id == "A_HELMET"
    assert pages[1].items[3].item_id == "B_BOOTS"


def test_parse_member_inventories_wardrobe_single_blob():
    from tests.test_nbt_inventory import _sample_blob, _wardrobe_set_blob

    payload = json.loads((FIXTURES / "profile_v2_sample.json").read_text(encoding="utf-8"))
    member = payload["profiles"][0]["members"]["28667672039044989b0019b14a2c34d6"]
    member["inventory"] = {
        "inv_contents": {"data": _sample_blob("ROCK")},
        "wardrobe_contents": {"data": _wardrobe_set_blob("HYPERION", "ROCK", "ASPECT_OF_THE_END", "ENCHANTED_DIAMOND")},
    }
    summary = parse_member_inventories(member)
    wardrobe = next(c for c in summary.containers if c.id == "wardrobe")
    assert wardrobe.page_count == 1
    assert wardrobe.filled_slots == 4


def test_parse_member_inventories_wardrobe_equipped_fallback_from_armor():
    from tests.test_nbt_inventory import _sample_blob

    payload = json.loads((FIXTURES / "profile_v2_sample.json").read_text(encoding="utf-8"))
    member = payload["profiles"][0]["members"]["28667672039044989b0019b14a2c34d6"]
    member["inventory"] = {
        "inv_contents": {"data": _sample_blob("ROCK")},
        "inv_armor": {"data": _sample_blob("BOOTS", "LEGS", "CHEST", "HELMET")},
        "wardrobe_equipped_slot": 4,
    }

    summary = parse_member_inventories(member)
    wardrobe = next(c for c in summary.containers if c.id == "wardrobe")
    assert wardrobe.status == "ok"
    assert wardrobe.page_count == 1
    assert wardrobe.filled_slots == 4
    assert wardrobe.equipped_set_index == 4
    assert wardrobe.layout == "armor_column"
    assert wardrobe.message is not None
    assert wardrobe.pages[0].items[0].item_id == "HELMET"
    assert wardrobe.pages[0].items[3].item_id == "BOOTS"


def test_parse_member_inventories_splits_backpack_and_wardrobe():
    from tests.test_nbt_inventory import _sample_blob

    payload = json.loads((FIXTURES / "profile_v2_sample.json").read_text(encoding="utf-8"))
    member = payload["profiles"][0]["members"]["28667672039044989b0019b14a2c34d6"]

    member["inventory"] = {
        "inv_contents": {"data": _sample_blob("ENCHANTED_DIAMOND")},
        "inv_armor": {"data": _sample_blob("HYPERION")},
        "equipment_contents": {"data": _sample_blob("ROCK")},
        "ender_chest_contents": {"data": _sample_blob("HYPERION")},
        "backpack_contents": {
            "0": {"data": _sample_blob("ROCK")},
            "wd1": {"data": _sample_blob("ASPECT_OF_THE_END")},
        },
        "wardrobe_contents": {
            "0": {"data": _sample_blob("HYPERION", "ROCK", "ASPECT_OF_THE_END", "ENCHANTED_DIAMOND")},
        },
        "bag_contents": {"talisman_bag": {"data": _sample_blob("ROCK", "HYPERION")}},
    }

    summary = parse_member_inventories(member)
    by_id = {container.id: container for container in summary.containers}

    assert [c.id for c in summary.containers] == list(CONTAINER_ORDER)
    assert by_id["backpack"].page_count == 1
    assert by_id["wardrobe"].page_count == 2
    assert by_id["accessory_bag"].label == "Accessory Bag"
    assert by_id["accessory_bag"].page_count >= 1
    assert by_id["armor_equipment"].layout == "armor_equipment"
    assert by_id["armor_equipment"].filled_slots >= 2


def test_parse_member_collections():
    from skyblock_agent.storage.collections_index import ensure_catalog

    ensure_catalog()
    member = {"collection": {"WHEAT": 1000, "CARROT_ITEM": 500, "COBBLESTONE": 200, "INK_SACK:3": 50, "LOTUS": 10}}
    summary = parse_member_collections(member)
    assert summary.available is True
    assert summary.total_items == 1760
    by_id = {entry.item_id: entry for entry in summary.entries}
    assert by_id["INK_SACK:3"].collection_type == "farming"
    assert by_id["INK_SACK:3"].display_name == "Cocoa Beans"
    assert by_id["LOTUS"].collection_type == "fishing"
    assert by_id["COBBLESTONE"].collection_type == "mining"
    assert len(summary.groups) == 3


def test_classify_collection_item_variants():
    from skyblock_agent.storage.collections_index import ensure_catalog

    ensure_catalog()
    assert classify_collection_item("LOG:1") == "foraging"
    assert classify_collection_item("RAW_FISH:2") == "fishing"
    assert classify_collection_item("INK_SACK:4") == "mining"
    assert classify_collection_item("INK_SACK:3") == "farming"
    assert classify_collection_item("SULPHUR") == "combat"
    assert classify_collection_item("SULPHUR_ORE") == "mining"
    assert classify_collection_item("WILTED_BERBERIS") == "rift"
    assert classify_collection_item("ENCHANTED_LEATHER") == "farming"
    assert classify_collection_item("CRUDE_GABAGOOL") == "other"
