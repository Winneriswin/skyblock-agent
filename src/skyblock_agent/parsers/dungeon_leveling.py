"""Catacombs / dungeon class XP to level (Hypixel dungeoneering table)."""

from __future__ import annotations

# XP required to advance from level N to N+1 (levels 0→1 through 49→50).
CATACOMBS_LEVEL_XP: tuple[int, ...] = (
    50,
    75,
    110,
    160,
    230,
    330,
    470,
    670,
    950,
    1340,
    1890,
    2665,
    3760,
    5260,
    7380,
    10300,
    14400,
    20000,
    27600,
    38000,
    52500,
    71500,
    97000,
    132000,
    180000,
    243000,
    328000,
    445000,
    600000,
    800000,
    1065000,
    1410000,
    1900000,
    2500000,
    3300000,
    4300000,
    5600000,
    7200000,
    9200000,
    12000000,
    15000000,
    19000000,
    24000000,
    30000000,
    38000000,
    48000000,
    60000000,
    75000000,
    93000000,
    116250000,
)

POST_MAX_OVERFLOW_XP = 200_000_000


def dungeon_level_from_experience(experience: float | None) -> float | None:
    if experience is None:
        return None
    try:
        exp = float(experience)
    except (TypeError, ValueError):
        return None
    if exp < 0:
        return None

    remaining = exp
    level = 0
    for requirement in CATACOMBS_LEVEL_XP:
        if remaining < requirement:
            return round(level + (remaining / requirement if requirement else 0.0), 2)
        remaining -= requirement
        level += 1

    overflow = remaining / POST_MAX_OVERFLOW_XP if POST_MAX_OVERFLOW_XP else 0.0
    return round(50 + overflow, 2)
