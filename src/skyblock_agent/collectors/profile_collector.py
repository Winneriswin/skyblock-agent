"""Fetch and resolve SkyBlock profiles for a player."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skyblock_agent.collectors.hypixel_client import HypixelApiError, HypixelClient
from skyblock_agent.collectors.mojang_client import MojangClient
from skyblock_agent.models.profile import (
    ProfileSummary,
    list_player_profiles,
    select_profile,
    summarize_profile,
)
from skyblock_agent.storage.raw_store import save_raw_json
from skyblock_agent.utils.uuid_utils import format_uuid_dashed, normalize_uuid


@dataclass
class PlayerProfileResult:
    username: str
    uuid: str
    hypixel_player: dict[str, Any] | None
    profiles_response: dict[str, Any]
    selected_profile: dict[str, Any]
    summary: ProfileSummary
    available_profiles: list[str]
    raw_paths: list[str]


class ProfileCollector:
    def __init__(
        self,
        hypixel: HypixelClient | None = None,
        mojang: MojangClient | None = None,
    ) -> None:
        self._owns_hypixel = hypixel is None
        self._owns_mojang = mojang is None
        self.hypixel = hypixel or HypixelClient()
        self.mojang = mojang or MojangClient()

    def fetch_by_username(
        self, username: str, *, profile_name: str | None = None
    ) -> PlayerProfileResult:
        uuid = self._resolve_uuid(username)
        if uuid is None:
            raise HypixelApiError(f"Player not found: {username}")
        return self.fetch_by_uuid(uuid, username=username, profile_name=profile_name)

    def _resolve_uuid(self, username: str) -> str | None:
        try:
            return self.mojang.lookup_uuid(username)
        except HypixelApiError:
            return self._lookup_uuid_via_hypixel(username)

    def _lookup_uuid_via_hypixel(self, username: str) -> str | None:
        try:
            payload = self.hypixel.get_player_by_username(username)
        except HypixelApiError:
            return None
        player = payload.get("player")
        if not isinstance(player, dict):
            return None
        raw_uuid = player.get("uuid")
        if isinstance(raw_uuid, str) and raw_uuid.strip():
            return normalize_uuid(raw_uuid)
        return None

    def fetch_by_uuid(
        self,
        uuid: str,
        *,
        username: str | None = None,
        profile_name: str | None = None,
    ) -> PlayerProfileResult:
        normalized = normalize_uuid(uuid)
        display_name = username or normalized

        player_payload: dict[str, Any] | None = None
        try:
            player_payload = self.hypixel.get_player(normalized)
            save_raw_json("player", normalized, player_payload)
        except HypixelApiError:
            player_payload = None

        profiles_payload = self.hypixel.get_skyblock_profiles(normalized)
        profiles_path = save_raw_json("profiles", normalized, profiles_payload)

        player_profiles = list_player_profiles(profiles_payload, normalized)
        available = [
            str(p.get("cute_name"))
            for p in player_profiles
            if isinstance(p.get("cute_name"), str)
        ]

        if not player_profiles:
            raise HypixelApiError(
                f"No SkyBlock profiles found for {display_name} "
                f"({format_uuid_dashed(normalized)})"
            )

        selected = select_profile(profiles_payload, normalized, profile_name)
        if selected is None:
            if profile_name:
                raise HypixelApiError(
                    f"Profile '{profile_name}' not found. Available: {', '.join(available)}"
                )
            raise HypixelApiError("Failed to select a SkyBlock profile.")

        summary = summarize_profile(selected, normalized)

        return PlayerProfileResult(
            username=display_name,
            uuid=format_uuid_dashed(normalized),
            hypixel_player=player_payload,
            profiles_response=profiles_payload,
            selected_profile=selected,
            summary=summary,
            available_profiles=available,
            raw_paths=[str(profiles_path)],
        )

    def close(self) -> None:
        if self._owns_hypixel:
            self.hypixel.close()
        if self._owns_mojang:
            self.mojang.close()

    def __enter__(self) -> ProfileCollector:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
