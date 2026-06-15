"""Look up a player by username and import Hypixel API data locally."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skyblock_agent.collectors.hypixel_client import HypixelApiError, HypixelClient
from skyblock_agent.collectors.mojang_client import MojangClient
from skyblock_agent.collectors.profile_collector import PlayerProfileResult, ProfileCollector
from skyblock_agent.models.profile import list_player_profiles, select_profile, summarize_profile
from skyblock_agent.storage.player_index import PlayerImportRecord, now_iso, upsert_player
from skyblock_agent.storage.raw_store import save_raw_json
from skyblock_agent.utils.uuid_utils import format_uuid_dashed, normalize_uuid


@dataclass
class LookupResult:
    profile: PlayerProfileResult
    import_record: PlayerImportRecord


class PlayerLookupService:
    """Resolve Minecraft username, fetch Hypixel API payloads, and persist locally."""

    def __init__(
        self,
        collector: ProfileCollector | None = None,
    ) -> None:
        self._owns_collector = collector is None
        self.collector = collector or ProfileCollector()

    def lookup(
        self,
        username: str,
        *,
        profile_name: str | None = None,
    ) -> LookupResult:
        name = username.strip()
        if not name:
            raise HypixelApiError("Username is required.")

        resolved_name, uuid = self._resolve_username(name)
        return self._import_resolved(resolved_name, uuid, profile_name=profile_name)

    def _resolve_username(self, username: str) -> tuple[str, str]:
        uuid = self.collector.mojang.lookup_uuid(username)
        if uuid is None:
            raise HypixelApiError(f"Player not found: {username}")

        display_name = username
        try:
            player_payload = self.collector.hypixel.get_player(uuid)
            player_obj = player_payload.get("player")
            if isinstance(player_obj, dict):
                display_name = str(player_obj.get("displayname") or player_obj.get("playername") or username)
        except HypixelApiError:
            display_name = username

        return display_name, uuid

    def _import_resolved(
        self,
        username: str,
        uuid: str,
        *,
        profile_name: str | None,
    ) -> LookupResult:
        normalized = normalize_uuid(uuid)
        saved_files: dict[str, str] = {}

        player_payload: dict[str, Any] | None = None
        try:
            player_payload = self.collector.hypixel.get_player(normalized)
            saved_files["player"] = str(save_raw_json("player", normalized, player_payload))
        except HypixelApiError:
            player_payload = None

        profiles_payload = self.collector.hypixel.get_skyblock_profiles(normalized)
        saved_files["profiles"] = str(save_raw_json("profiles", normalized, profiles_payload))

        player_profiles = list_player_profiles(profiles_payload, normalized)
        available = [
            str(p.get("cute_name"))
            for p in player_profiles
            if isinstance(p.get("cute_name"), str)
        ]

        if not player_profiles:
            raise HypixelApiError(
                f"No SkyBlock profiles found for {username} ({format_uuid_dashed(normalized)})"
            )

        selected = select_profile(profiles_payload, normalized, profile_name)
        if selected is None:
            if profile_name:
                raise HypixelApiError(
                    f"Profile '{profile_name}' not found. Available: {', '.join(available)}"
                )
            raise HypixelApiError("Failed to select a SkyBlock profile.")

        profile_id = str(selected.get("profile_id", normalized))
        saved_files["selected_profile"] = str(
            save_raw_json("selected_profile", profile_id, selected)
        )

        summary = summarize_profile(selected, normalized)
        import_record = PlayerImportRecord(
            username=username,
            uuid=format_uuid_dashed(normalized),
            last_imported_at=now_iso(),
            profiles=available,
            selected_profile=summary.cute_name,
            saved_files=saved_files,
        )
        upsert_player(import_record)

        profile_result = PlayerProfileResult(
            username=username,
            uuid=format_uuid_dashed(normalized),
            hypixel_player=player_payload,
            profiles_response=profiles_payload,
            selected_profile=selected,
            summary=summary,
            available_profiles=available,
            raw_paths=list(saved_files.values()),
        )
        return LookupResult(profile=profile_result, import_record=import_record)

    def close(self) -> None:
        if self._owns_collector:
            self.collector.close()

    def __enter__(self) -> PlayerLookupService:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
