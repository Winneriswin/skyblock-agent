"""Normalize member map keys to dashless lowercase UUIDs."""

from __future__ import annotations

from typing import Any

from skyblock_agent.utils.uuid_utils import normalize_uuid


def normalize_member_map(members: Any) -> dict[str, Any]:
    if not isinstance(members, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key, value in members.items():
        if isinstance(key, str) and isinstance(value, dict):
            normalized[normalize_uuid(key)] = value
    return normalized


def get_member(members: Any, player_uuid: str) -> dict[str, Any]:
    mapping = normalize_member_map(members)
    member = mapping.get(normalize_uuid(player_uuid))
    return member if isinstance(member, dict) else {}
