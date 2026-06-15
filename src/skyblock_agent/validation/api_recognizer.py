"""Inspect Hypixel API payloads and report which fields are recognized."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Literal

from skyblock_agent.models.members import get_member, normalize_member_map
from skyblock_agent.models.profile import (
    SKILL_KEYS,
    SLAYER_KEYS,
    _nested_get,
    skills_api_enabled,
    skyblock_level,
)
from skyblock_agent.utils.uuid_utils import normalize_uuid

FieldStatusKind = Literal["ok", "missing", "hidden", "empty"]


@dataclass
class FieldCheck:
    path: str
    label: str
    status: FieldStatusKind
    detail: str | None = None


@dataclass
class RecognitionReport:
    username: str
    uuid: str
    profile_name: str
    profile_id: str
    checks: list[FieldCheck] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for check in self.checks if check.status == "ok")

    @property
    def total_count(self) -> int:
        return len(self.checks)

    @property
    def pass_rate(self) -> float:
        if not self.checks:
            return 0.0
        return self.ok_count / len(self.checks)

    @property
    def all_required_ok(self) -> bool:
        required = {
            "profile.cute_name",
            "profile.profile_id",
            "member.leveling.experience",
        }
        by_path = {check.path: check.status for check in self.checks}
        return all(by_path.get(path) == "ok" for path in required)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ok_count"] = self.ok_count
        payload["total_count"] = self.total_count
        payload["pass_rate"] = round(self.pass_rate, 4)
        payload["all_required_ok"] = self.all_required_ok
        return payload


def _check(
    checks: list[FieldCheck],
    *,
    path: str,
    label: str,
    present: bool,
    hidden: bool = False,
    has_value: bool = True,
    detail: str | None = None,
) -> None:
    if hidden:
        status: FieldStatusKind = "hidden"
    elif not present:
        status = "missing"
    elif not has_value:
        status = "empty"
    else:
        status = "ok"
    checks.append(FieldCheck(path=path, label=label, status=status, detail=detail))


def _skill_detail(member: dict[str, Any], skill: str) -> tuple[bool, bool, str | None]:
    key = f"SKILL_{skill.upper()}"
    raw = _nested_get(member, "player_data", "experience", key)
    if raw is None:
        return False, False, None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return True, False, "invalid number"
    if value < 0:
        return True, True, "API hidden (-1)"
    return True, True, f"{value:,.0f} XP"


def recognize_profile_member(
    *,
    username: str,
    uuid: str,
    profile: dict[str, Any],
    player_uuid: str,
) -> RecognitionReport:
    member = get_member(profile.get("members"), player_uuid)
    checks: list[FieldCheck] = []

    _check(
        checks,
        path="profile.cute_name",
        label="Profile name",
        present="cute_name" in profile,
        has_value=bool(profile.get("cute_name")),
        detail=str(profile.get("cute_name")) if profile.get("cute_name") else None,
    )
    _check(
        checks,
        path="profile.profile_id",
        label="Profile ID",
        present="profile_id" in profile,
        has_value=bool(profile.get("profile_id")),
        detail=str(profile.get("profile_id")) if profile.get("profile_id") else None,
    )
    _check(
        checks,
        path="profile.selected",
        label="Selected profile flag",
        present="selected" in profile,
        has_value=True,
        detail="selected" if profile.get("selected") else "not selected",
    )
    _check(
        checks,
        path="profile.game_mode",
        label="Game mode",
        present=profile.get("game_mode") is not None,
        has_value=bool(profile.get("game_mode")),
        detail=str(profile.get("game_mode") or "normal"),
    )

    members = normalize_member_map(profile.get("members"))
    _check(
        checks,
        path="profile.members",
        label="Coop members",
        present=bool(members),
        has_value=len(members) > 0,
        detail=f"{len(members)} member(s)",
    )

    sb_level = skyblock_level(member)
    _check(
        checks,
        path="member.leveling.experience",
        label="SkyBlock level XP",
        present=_nested_get(member, "leveling", "experience") is not None,
        has_value=sb_level is not None,
        detail=f"level {sb_level:.2f}" if sb_level is not None else None,
    )

    api_on = skills_api_enabled(member)
    _check(
        checks,
        path="member.player_data.experience",
        label="Skills API",
        present=_nested_get(member, "player_data", "experience") is not None,
        hidden=not api_on and _nested_get(member, "player_data", "experience") is not None,
        has_value=api_on,
        detail="enabled" if api_on else "disabled in-game",
    )

    for skill in SKILL_KEYS:
        present, has_value, detail = _skill_detail(member, skill)
        hidden = present and detail == "API hidden (-1)"
        _check(
            checks,
            path=f"member.player_data.experience.SKILL_{skill.upper()}",
            label=f"Skill: {skill}",
            present=present,
            hidden=hidden,
            has_value=has_value and not hidden,
            detail=detail,
        )

    slayer_root = _nested_get(member, "slayer", "slayer_bosses")
    _check(
        checks,
        path="member.slayer.slayer_bosses",
        label="Slayer data root",
        present=isinstance(slayer_root, dict),
        has_value=bool(slayer_root),
    )

    for slayer in SLAYER_KEYS:
        boss = slayer_root.get(slayer) if isinstance(slayer_root, dict) else None
        xp = None
        if isinstance(boss, dict):
            try:
                xp = float(boss.get("xp", 0) or 0)
            except (TypeError, ValueError):
                xp = 0.0
        _check(
            checks,
            path=f"member.slayer.slayer_bosses.{slayer}",
            label=f"Slayer: {slayer}",
            present=isinstance(boss, dict),
            has_value=isinstance(boss, dict) and (xp or 0) > 0,
            detail=f"{xp:,.0f} XP" if isinstance(boss, dict) and xp else None,
        )

    cata_exp = _nested_get(member, "dungeons", "dungeon_types", "catacombs", "experience")
    _check(
        checks,
        path="member.dungeons.dungeon_types.catacombs.experience",
        label="Catacombs XP",
        present=cata_exp is not None,
        has_value=bool(cata_exp),
        detail=f"{float(cata_exp):,.0f} XP" if cata_exp is not None else None,
    )

    optional_sections: list[tuple[str, str, Callable[[dict[str, Any]], Any]]] = [
        ("member.collection", "Collections", lambda m: m.get("collection")),
        ("member.inventory", "Inventory", lambda m: m.get("inventory")),
        ("member.pets_data", "Pets", lambda m: m.get("pets_data")),
        ("member.mining_core", "Mining core", lambda m: m.get("mining_core")),
        ("member.garden_player_data", "Garden", lambda m: m.get("garden_player_data")),
        ("member.nether_island_player_data", "Nether", lambda m: m.get("nether_island_player_data")),
        ("member.bestiary", "Bestiary", lambda m: m.get("bestiary")),
    ]
    for path, label, getter in optional_sections:
        value = getter(member)
        _check(
            checks,
            path=path,
            label=label,
            present=value is not None,
            has_value=bool(value),
        )

    return RecognitionReport(
        username=username,
        uuid=uuid,
        profile_name=str(profile.get("cute_name", "Unknown")),
        profile_id=str(profile.get("profile_id", "")),
        checks=checks,
    )


def recognize_player_result(result) -> RecognitionReport:
    normalized = normalize_uuid(result.uuid)
    return recognize_profile_member(
        username=result.username,
        uuid=result.uuid,
        profile=result.selected_profile,
        player_uuid=normalized,
    )
