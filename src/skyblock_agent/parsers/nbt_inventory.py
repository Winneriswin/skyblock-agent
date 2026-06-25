"""Decode Hypixel SkyBlock inventory blobs (base64 + gzip + NBT)."""

from __future__ import annotations

import base64
import gzip
import io
import re
from typing import Any

from skyblock_agent.models.inventory import ItemStack

_COLOR_CODE = re.compile(r"§[0-9a-fk-or]", re.IGNORECASE)
_AMP_COLOR = re.compile(r"&[0-9a-fk-or]", re.IGNORECASE)


def strip_color_codes(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = _COLOR_CODE.sub("", text)
    cleaned = _AMP_COLOR.sub("", cleaned)
    cleaned = cleaned.strip()
    return cleaned or None


def extract_encoded_data(raw: Any) -> str | None:
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, dict):
        data = raw.get("data")
        if isinstance(data, str) and data.strip():
            return data.strip()
    return None


def decode_inventory_blob(encoded: str) -> bytes:
    try:
        compressed = base64.b64decode(encoded, validate=False)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid base64 inventory data") from exc
    try:
        return gzip.decompress(compressed)
    except OSError as exc:
        raise ValueError("Invalid gzip inventory data") from exc


def parse_inventory_blob(encoded: str) -> list[ItemStack]:
    payload = decode_inventory_blob(encoded)
    return parse_nbt_item_list(payload)


def parse_nbt_item_list(payload: bytes) -> list[ItemStack]:
    try:
        from nbtlib import File
    except ImportError as exc:
        raise RuntimeError(
            "nbtlib is required for inventory parsing. Install with: pip install nbtlib"
        ) from exc

    try:
        parsed = File.parse(io.BytesIO(payload))
    except (ValueError, TypeError, OSError, KeyError) as exc:
        raise ValueError(f"Failed to parse inventory NBT: {exc}") from exc

    items_raw = _find_item_list(parsed)
    if items_raw is None:
        return []

    stacks: list[ItemStack] = []
    for index, entry in enumerate(items_raw):
        stack = _parse_item_compound(entry, fallback_slot=index)
        if stack is not None:
            stacks.append(stack)
    stacks.sort(key=lambda item: item.slot)
    return stacks


def _find_item_list(parsed: Any) -> list[Any] | None:
    if hasattr(parsed, "get"):
        for key in ("i", "items"):
            value = parsed.get(key)
            if value is not None:
                return list(value)
    return None


def _parse_item_compound(entry: Any, *, fallback_slot: int) -> ItemStack | None:
    if not hasattr(entry, "get"):
        return None

    slot = _read_int(entry.get("Slot"), default=fallback_slot)
    count = max(1, _read_int(entry.get("Count"), default=1))

    tag = entry.get("tag")
    item_id: str | None = None
    name: str | None = None
    lore: list[str] = []

    if hasattr(tag, "get"):
        extra = tag.get("ExtraAttributes")
        if hasattr(extra, "get"):
            raw_id = extra.get("id")
            if raw_id is not None:
                item_id = str(raw_id)

        display = tag.get("display")
        if hasattr(display, "get"):
            raw_name = display.get("Name")
            if raw_name is not None:
                name = str(raw_name)
            raw_lore = display.get("Lore")
            if raw_lore is not None:
                lore = [str(line) for line in raw_lore if str(line).strip()]

    if not item_id and not name and count <= 0:
        return None

    display_name = strip_color_codes(name) or (
        item_id.replace("_", " ") if item_id else None
    )
    return ItemStack(
        slot=slot,
        item_id=item_id,
        name=name,
        display_name=display_name,
        lore=lore,
        count=count,
    )


def _read_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
