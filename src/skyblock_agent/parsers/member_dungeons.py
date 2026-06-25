"""Parse Catacombs stats from a SkyBlock profile member payload."""

from __future__ import annotations

from typing import Any

from skyblock_agent.models.dungeons import (
    DUNGEON_CLASS_LABELS,
    DUNGEON_CLASS_ORDER,
    CatacombsSummary,
    DungeonClassInfo,
    DungeonFloorStats,
    DungeonModeStats,
)
from skyblock_agent.parsers.dungeon_leveling import dungeon_level_from_experience

NORMAL_FLOOR_LABELS: dict[int, str] = {
    0: "Entrance",
    1: "F1",
    2: "F2",
    3: "F3",
    4: "F4",
    5: "F5",
    6: "F6",
    7: "F7",
}


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _parse_count_map(raw: Any) -> dict[int, int]:
    if not isinstance(raw, dict):
        return {}
    result: dict[int, int] = {}
    for key, value in raw.items():
        try:
            floor = int(key)
            count = int(float(value))
        except (TypeError, ValueError):
            continue
        if count > 0:
            result[floor] = count
    return result


def _parse_time_map(raw: Any) -> dict[int, float]:
    if not isinstance(raw, dict):
        return {}
    result: dict[int, float] = {}
    for key, value in raw.items():
        try:
            floor = int(key)
            ms = float(value)
        except (TypeError, ValueError):
            continue
        if ms > 0:
            result[floor] = ms
    return result


def _build_floors(
    *,
    floor_numbers: tuple[int, ...],
    label_for_floor,
    completions_raw: Any,
    pb_s_raw: Any,
    pb_s_plus_raw: Any,
) -> list[DungeonFloorStats]:
    completions = _parse_count_map(completions_raw)
    pb_s = _parse_time_map(pb_s_raw)
    pb_s_plus = _parse_time_map(pb_s_plus_raw)

    floors: list[DungeonFloorStats] = []
    for floor in floor_numbers:
        count = completions.get(floor, 0)
        s_ms = pb_s.get(floor)
        s_plus_ms = pb_s_plus.get(floor)
        if count <= 0 and s_ms is None and s_plus_ms is None:
            continue
        floors.append(
            DungeonFloorStats(
                floor=floor,
                label=label_for_floor(floor),
                completions=count,
                pb_s_ms=s_ms,
                pb_s_plus_ms=s_plus_ms,
            )
        )
    return floors


def _parse_classes(dungeons_root: dict[str, Any]) -> list[DungeonClassInfo]:
    raw_classes = dungeons_root.get("player_classes")
    selected = dungeons_root.get("selected_dungeon_class")
    selected_key = str(selected).lower() if isinstance(selected, str) else None

    classes: list[DungeonClassInfo] = []
    if not isinstance(raw_classes, dict):
        return classes

    for class_id in DUNGEON_CLASS_ORDER:
        entry = raw_classes.get(class_id)
        if not isinstance(entry, dict):
            continue
        try:
            experience = float(entry.get("experience") or 0)
        except (TypeError, ValueError):
            experience = 0.0
        if experience <= 0 and selected_key != class_id:
            continue
        level = dungeon_level_from_experience(experience) or 0.0
        classes.append(
            DungeonClassInfo(
                id=class_id,
                label=DUNGEON_CLASS_LABELS[class_id],
                experience=experience,
                level=level,
                selected=selected_key == class_id,
            )
        )
    return classes


def parse_member_dungeons(member: dict[str, Any]) -> CatacombsSummary:
    dungeons_root = member.get("dungeons")
    if not isinstance(dungeons_root, dict):
        return CatacombsSummary(available=False, message="No dungeon data in API response.")

    dungeon_types = dungeons_root.get("dungeon_types")
    if not isinstance(dungeon_types, dict):
        return CatacombsSummary(available=False, message="No dungeon types in API response.")

    catacombs = dungeon_types.get("catacombs")
    master = dungeon_types.get("master_catacombs")
    if not isinstance(catacombs, dict) and not isinstance(master, dict):
        return CatacombsSummary(available=False, message="Catacombs data not found.")

    experience: float | None = None
    if isinstance(catacombs, dict):
        try:
            raw_exp = catacombs.get("experience")
            experience = float(raw_exp) if raw_exp is not None else None
        except (TypeError, ValueError):
            experience = None

    selected = dungeons_root.get("selected_dungeon_class")
    selected_key = str(selected).lower() if isinstance(selected, str) else None
    selected_label = DUNGEON_CLASS_LABELS.get(selected_key) if selected_key else None

    modes: list[DungeonModeStats] = []
    if isinstance(catacombs, dict):
        normal_floors = _build_floors(
            floor_numbers=tuple(range(8)),
            label_for_floor=lambda floor: NORMAL_FLOOR_LABELS.get(floor, f"F{floor}"),
            completions_raw=catacombs.get("tier_completions"),
            pb_s_raw=catacombs.get("fastest_time_s"),
            pb_s_plus_raw=catacombs.get("fastest_time_s_plus"),
        )
        modes.append(DungeonModeStats(mode="normal", label="Catacombs", floors=normal_floors))

    if isinstance(master, dict):
        master_floors = _build_floors(
            floor_numbers=tuple(range(1, 8)),
            label_for_floor=lambda floor: f"M{floor}",
            completions_raw=master.get("tier_completions"),
            pb_s_raw=master.get("fastest_time_s"),
            pb_s_plus_raw=master.get("fastest_time_s_plus"),
        )
        modes.append(DungeonModeStats(mode="master", label="Master Mode", floors=master_floors))

    classes = _parse_classes(dungeons_root)
    has_data = bool(modes) or experience is not None or classes
    if not has_data:
        return CatacombsSummary(available=False, message="No Catacombs progress recorded.")

    return CatacombsSummary(
        available=True,
        experience=experience,
        level=dungeon_level_from_experience(experience),
        selected_class=selected_key,
        selected_class_label=selected_label,
        classes=classes,
        modes=modes,
    )
