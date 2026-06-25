"""Build minetip title/text from player item NBT (name + lore)."""

from __future__ import annotations

import re
from typing import Any

from skyblock_agent.parsers.nbt_inventory import strip_color_codes

_COLOR = re.compile(r"[§&][0-9a-fk-or]", re.IGNORECASE)


def normalize_color_codes(text: str | None) -> str:
    if not text:
        return ""
    return str(text).replace("§", "&")


def _plain(text: str | None) -> str:
    if not text:
        return ""
    return _COLOR.sub("", normalize_color_codes(text)).strip()


def minetip_from_item_dict(item: dict[str, Any]) -> dict[str, str]:
    """Convert API/NBT item fields to minetip ``title`` and ``text``."""
    raw_name = item.get("name") or item.get("display_name") or item.get("item_id") or "Unknown"
    title = normalize_color_codes(str(raw_name))
    if not title.startswith("&"):
        title = f"&f{title}"

    lore = item.get("lore") or []
    lore_lines = [normalize_color_codes(str(line)) for line in lore if str(line).strip()]

    body_lines = list(lore_lines)
    if body_lines and _plain(body_lines[0]) == _plain(raw_name):
        body_lines = body_lines[1:]

    text_parts = body_lines
    count = int(item.get("count") or 1)
    if count > 1:
        text_parts.append(f"&7Count: &f{count}")

    item_id = item.get("item_id")
    if item_id:
        text_parts.append(f"&8{item_id}")

    return {"title": title, "text": "/".join(text_parts)}
