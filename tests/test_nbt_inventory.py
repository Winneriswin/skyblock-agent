"""Tests for Hypixel inventory NBT parsing."""

import base64
import gzip
import io
import json
from pathlib import Path

import nbtlib
from nbtlib import Byte, Compound, List, Short, String

from skyblock_agent.models.inventory import InventoriesSummary
from skyblock_agent.parsers.member_inventories import CONTAINER_ORDER, parse_member_inventories
from skyblock_agent.parsers.nbt_inventory import parse_inventory_blob, strip_color_codes

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _encode_item_list(items: List[Compound]) -> str:
    root = Compound({"i": items})
    buf = io.BytesIO()
    nbtlib.File(root).write(buf)
    return base64.b64encode(gzip.compress(buf.getvalue())).decode("ascii")


def _sample_blob(*item_ids: str) -> str:
    entries = []
    for slot, item_id in enumerate(item_ids):
        entries.append(
            Compound(
                {
                    "Slot": Byte(slot),
                    "id": Short(276),
                    "Count": Byte(1),
                    "tag": Compound(
                        {
                            "ExtraAttributes": Compound({"id": String(item_id)}),
                            "display": Compound(
                                {
                                    "Name": String(f"§a{item_id.replace('_', ' ')}"),
                                    "Lore": List[String]([String("§7Test lore")]),
                                }
                            ),
                        }
                    ),
                }
            )
        )
    return _encode_item_list(List[Compound](entries))


def _wardrobe_set_blob(*item_ids: str) -> str:
    """Encode one wardrobe set at slots 0/9/18/27 (in-game column layout)."""
    entries = []
    for slot, item_id in zip((0, 9, 18, 27), item_ids):
        entries.append(
            Compound(
                {
                    "Slot": Byte(slot),
                    "id": Short(276),
                    "Count": Byte(1),
                    "tag": Compound(
                        {
                            "ExtraAttributes": Compound({"id": String(item_id)}),
                            "display": Compound({"Name": String(f"§a{item_id}")}),
                        }
                    ),
                }
            )
        )
    return _encode_item_list(List[Compound](entries))


def test_strip_color_codes():
    assert strip_color_codes("§9Aspect of the End") == "Aspect of the End"


def test_parse_inventory_blob():
    blob = _sample_blob("ENCHANTED_DIAMOND", "ASPECT_OF_THE_END")
    stacks = parse_inventory_blob(blob)
    assert len(stacks) == 2
    assert stacks[0].item_id == "ENCHANTED_DIAMOND"
    assert stacks[1].slot == 1
    assert stacks[1].lore == ["§7Test lore"]


def test_parse_member_inventories_from_fixture():
    payload = json.loads((FIXTURES / "profile_v2_sample.json").read_text(encoding="utf-8"))
    profile = payload["profiles"][0]
    member = profile["members"]["28667672039044989b0019b14a2c34d6"]

    blob = _sample_blob("ENCHANTED_DIAMOND")
    member["inventory"] = {
        "inv_contents": {"data": blob},
        "ender_chest_contents": {"data": _sample_blob("HYPERION")},
        "bag_contents": {"talisman_bag": {"data": _sample_blob("ROCK")}},
    }
    summary = parse_member_inventories(member)
    assert isinstance(summary, InventoriesSummary)
    assert summary.inventory_api_enabled is True

    by_id = {container.id: container for container in summary.containers}
    assert by_id["inventory"].status == "ok"
    assert by_id["inventory"].items[0].item_id == "ENCHANTED_DIAMOND"
    assert by_id["ender_chest"].filled_slots == 1
    assert by_id["accessory_bag"].filled_slots == 1
    assert by_id["backpack"].status == "hidden"
    assert by_id["armor_equipment"].status == "hidden"


def test_parse_member_inventories_hidden_when_missing():
    summary = parse_member_inventories({})
    assert summary.inventory_api_enabled is False
    assert all(container.status == "hidden" for container in summary.containers)
    assert [container.id for container in summary.containers] == list(CONTAINER_ORDER)
