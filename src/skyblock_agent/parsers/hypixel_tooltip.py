"""Build base minetip lines from Hypixel items resource stats."""

from __future__ import annotations

from typing import Any

TIER_COLOR: dict[str, str] = {
    "COMMON": "f",
    "UNCOMMON": "a",
    "RARE": "9",
    "EPIC": "5",
    "LEGENDARY": "6",
    "MYTHIC": "d",
    "SPECIAL": "c",
    "VERY_SPECIAL": "c",
    "SUPREME": "4",
    "ADMIN": "4",
}

STAT_FORMAT: dict[str, tuple[str, str]] = {
    "DAMAGE": ("Damage", "c"),
    "STRENGTH": ("Strength", "c"),
    "DEFENSE": ("Defense", "a"),
    "HEALTH": ("Health", "a"),
    "INTELLIGENCE": ("Intelligence", "b"),
    "WALK_SPEED": ("Walk Speed", "f"),
    "CRITICAL_CHANCE": ("Crit Chance", "9"),
    "CRITICAL_DAMAGE": ("Crit Damage", "9"),
    "ATTACK_SPEED": ("Bonus Attack Speed", "e"),
    "FEROCITY": ("Ferocity", "c"),
    "MAGIC_FIND": ("Magic Find", "b"),
    "SEA_CREATURE_CHANCE": ("Sea Creature Chance", "c"),
    "FISHING_SPEED": ("Fishing Speed", "6"),
}


def tier_color_code(tier: str | None) -> str:
    if not tier:
        return "7"
    return TIER_COLOR.get(str(tier).upper(), "7")


def format_stat_line(stat_key: str, value: Any) -> str | None:
    label, color = STAT_FORMAT.get(stat_key, (stat_key.replace("_", " ").title(), "7"))
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if stat_key.endswith("_CHANCE") or stat_key.endswith("_DAMAGE") and stat_key != "DAMAGE":
        suffix = "%" if stat_key.endswith("_CHANCE") else ""
        if number == int(number):
            return f"&7{label}: &{color}{int(number)}{suffix}"
        return f"&7{label}: &{color}{number:g}{suffix}"
    if number == int(number):
        return f"&7{label}: &{color}+{int(number)}"
    return f"&7{label}: &{color}+{number:g}"


def build_hypixel_base_tooltip(item: dict[str, Any]) -> dict[str, Any] | None:
    """Return minetip fields generated from Hypixel resource stats (blank profile)."""
    item_id = str(item.get("id") or "").strip()
    name = str(item.get("name") or item_id)
    if not item_id:
        return None

    tier = item.get("tier")
    color = tier_color_code(str(tier) if tier else None)
    title = f"&{color}{name}"

    stats = item.get("stats")
    if not isinstance(stats, dict) or not stats:
        return None

    lines: list[str] = []
    for stat_key in sorted(stats.keys()):
        line = format_stat_line(stat_key, stats[stat_key])
        if line:
            lines.append(line)

    category = item.get("category")
    if category:
        lines.append(f"&8{item_id}")
        if tier:
            lines.append(f"&{color}&l{tier} {category}")
        else:
            lines.append(f"&7{category}")
    else:
        lines.append(f"&8{item_id}")

    return {
        "item_id": item_id,
        "title": title,
        "text": "/".join(lines),
        "lore": None,
        "source": "hypixel",
    }
