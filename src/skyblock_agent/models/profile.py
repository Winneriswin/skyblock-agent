"""Parse SkyBlock profile JSON (logic adapted from NEU SkyblockProfiles / Skyblocker models)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skyblock_agent.models.members import get_member, normalize_member_map
from skyblock_agent.utils.uuid_utils import normalize_uuid


SKILL_KEYS = (
    "combat",
    "mining",
    "foraging",
    "farming",
    "enchanting",
    "fishing",
    "alchemy",
    "taming",
    "carpentry",
    "runecrafting",
    "social",
)

SLAYER_KEYS = ("zombie", "spider", "wolf", "enderman", "blaze", "vampire")


@dataclass
class SkillInfo:
    name: str
    experience: float | None
    api_enabled: bool


@dataclass
class SlayerInfo:
    name: str
    level: int
    xp: float


@dataclass
class ProfileSummary:
    cute_name: str
    profile_id: str
    selected: bool
    game_mode: str | None
    skyblock_level: float | None
    skills_api_enabled: bool
    skills: list[SkillInfo] = field(default_factory=list)
    slayers: list[SlayerInfo] = field(default_factory=list)
    catacombs_level: float | None = None
    member_count: int = 0


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def skills_api_enabled(member: dict[str, Any]) -> bool:
    """NEU checks SKILL_COMBAT != -1 when API settings hide skills."""
    exp = _nested_get(member, "player_data", "experience", "SKILL_COMBAT")
    if exp is None:
        return False
    try:
        return float(exp) >= 0
    except (TypeError, ValueError):
        return False


def skyblock_level(member: dict[str, Any]) -> float | None:
    exp = _nested_get(member, "leveling", "experience")
    if exp is None:
        return None
    try:
        return float(exp) / 100.0
    except (TypeError, ValueError):
        return None


def parse_skills(member: dict[str, Any]) -> list[SkillInfo]:
    enabled = skills_api_enabled(member)
    skills: list[SkillInfo] = []
    experience = _nested_get(member, "player_data", "experience") or {}

    for skill in SKILL_KEYS:
        key = f"SKILL_{skill.upper()}"
        raw = experience.get(key) if isinstance(experience, dict) else None
        value: float | None
        if raw is None:
            value = None
        else:
            try:
                parsed = float(raw)
                value = None if parsed < 0 else parsed
            except (TypeError, ValueError):
                value = None
        skills.append(SkillInfo(name=skill, experience=value, api_enabled=enabled))
    return skills


def _slayer_level(boss: dict[str, Any]) -> int:
    claimed_levels = boss.get("claimed_levels")
    if isinstance(claimed_levels, dict):
        return sum(1 for value in claimed_levels.values() if value)

    residents = boss.get("claimed_residents")
    if isinstance(residents, dict):
        try:
            return int(residents.get("level", 0) or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def parse_slayers(member: dict[str, Any]) -> list[SlayerInfo]:
    slayer_root = _nested_get(member, "slayer", "slayer_bosses") or {}
    if not isinstance(slayer_root, dict):
        return []

    result: list[SlayerInfo] = []
    for name in SLAYER_KEYS:
        boss = slayer_root.get(name)
        if not isinstance(boss, dict):
            continue
        level = _slayer_level(boss)
        try:
            xp = float(boss.get("xp", 0) or 0)
        except (TypeError, ValueError):
            xp = 0.0
        result.append(SlayerInfo(name=name, level=level, xp=xp))
    return result


def catacombs_level(member: dict[str, Any]) -> float | None:
    exp = _nested_get(member, "dungeons", "dungeon_types", "catacombs", "experience")
    if exp is None:
        return None
    try:
        # Full level formula needs constants; show raw XP / 100 as rough indicator.
        return float(exp) / 100.0
    except (TypeError, ValueError):
        return None


def is_confirmed_member(member: dict[str, Any]) -> bool:
    """Skip unconfirmed coop invitations (NEU SkyblockProfiles logic)."""
    invitation = member.get("coop_invitation")
    if not isinstance(invitation, dict):
        return True
    return bool(invitation.get("confirmed", False))


def list_player_profiles(
    profiles_response: dict[str, Any], player_uuid: str
) -> list[dict[str, Any]]:
    profiles = profiles_response.get("profiles")
    if profiles is None:
        return []

    result: list[dict[str, Any]] = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        members = normalize_member_map(profile.get("members"))
        if not members:
            continue
        member = members.get(normalize_uuid(player_uuid))
        if not isinstance(member, dict):
            continue
        if not is_confirmed_member(member):
            continue
        result.append(profile)
    return result


def select_profile(
    profiles_response: dict[str, Any],
    player_uuid: str,
    profile_name: str | None = None,
) -> dict[str, Any] | None:
    profiles = list_player_profiles(profiles_response, player_uuid)
    if not profiles:
        return None

    if profile_name:
        target = profile_name.lower()
        for profile in profiles:
            cute_name = profile.get("cute_name", "")
            if isinstance(cute_name, str) and cute_name.lower() == target:
                return profile
        return None

    for profile in profiles:
        if profile.get("selected"):
            return profile

    return profiles[0]


def summarize_profile(profile: dict[str, Any], player_uuid: str) -> ProfileSummary:
    members = normalize_member_map(profile.get("members"))
    member = get_member(members, player_uuid)

    return ProfileSummary(
        cute_name=str(profile.get("cute_name", "Unknown")),
        profile_id=str(profile.get("profile_id", "")),
        selected=bool(profile.get("selected")),
        game_mode=profile.get("game_mode") if isinstance(profile.get("game_mode"), str) else None,
        skyblock_level=skyblock_level(member),
        skills_api_enabled=skills_api_enabled(member),
        skills=parse_skills(member),
        slayers=parse_slayers(member),
        catacombs_level=catacombs_level(member),
        member_count=len(members),
    )
