"""Tests for player lookup import flow."""

import json
from unittest.mock import MagicMock

from skyblock_agent.collectors.player_lookup import PlayerLookupService
from skyblock_agent.storage.player_index import get_player, list_players


FIXTURE_PROFILES = {
    "success": True,
    "profiles": [
        {
            "cute_name": "Apple",
            "profile_id": "profile-uuid-1",
            "selected": True,
            "members": {
                "28667672039044989b0019b14a2c34d6": {
                    "leveling": {"experience": 4200},
                    "player_data": {"experience": {"SKILL_COMBAT": 1000}},
                }
            },
        }
    ],
}

FIXTURE_PLAYER = {
    "success": True,
    "player": {
        "displayname": "SamplePlayer",
        "uuid": "28667672039044989b0019b14a2c34d6",
    },
}


def test_lookup_imports_and_indexes(tmp_path, monkeypatch):
    monkeypatch.setenv("SKYBLOCK_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HYPIXEL_API_KEY", "test-key")

    from skyblock_agent import config

    config.DATA_DIR = tmp_path
    config.RAW_HYPIXEL_DIR = tmp_path / "raw" / "hypixel_api"

    from skyblock_agent.storage import player_index, raw_store

    player_index.INDEX_PATH = tmp_path / "processed" / "players" / "index.json"
    raw_store.RAW_HYPIXEL_DIR = tmp_path / "raw" / "hypixel_api"

    hypixel = MagicMock()
    hypixel.get_player.return_value = FIXTURE_PLAYER
    hypixel.get_skyblock_profiles.return_value = FIXTURE_PROFILES

    mojang = MagicMock()
    mojang.lookup_uuid.return_value = "28667672039044989b0019b14a2c34d6"

    from skyblock_agent.collectors.profile_collector import ProfileCollector

    collector = ProfileCollector(hypixel=hypixel, mojang=mojang)
    service = PlayerLookupService(collector=collector)

    lookup = service.lookup("SamplePlayer")

    assert lookup.profile.username == "SamplePlayer"
    assert lookup.import_record.username == "SamplePlayer"
    assert "player" in lookup.import_record.saved_files
    assert "profiles" in lookup.import_record.saved_files
    assert "selected_profile" in lookup.import_record.saved_files

    saved = get_player("SamplePlayer")
    assert saved is not None
    assert saved.uuid == "28667672-0390-4498-9b00-19b14a2c34d6"
    assert saved.profiles == ["Apple"]

    player_file = tmp_path / "raw" / "hypixel_api" / "player" / "28667672039044989b0019b14a2c34d6.json"
    assert player_file.exists()
    payload = json.loads(player_file.read_text(encoding="utf-8"))
    assert payload["data"]["success"] is True

    indexed = list_players()
    assert len(indexed) == 1
