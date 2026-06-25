"""Tests for Mojang username lookup fallbacks."""

from unittest.mock import MagicMock

import pytest
import requests

from skyblock_agent.collectors.hypixel_client import HypixelApiError
from skyblock_agent.collectors.mojang_client import MojangClient
from skyblock_agent.collectors.profile_collector import ProfileCollector


def test_lookup_uuid_primary_provider():
    client = MojangClient(max_retries=1)
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"id": "28667672039044989b0019b14a2c34d6", "name": "Refraction"}
    client._session.get = MagicMock(return_value=response)

    assert client.lookup_uuid("Refraction") == "28667672039044989b0019b14a2c34d6"
    client._session.get.assert_called_once()


def test_lookup_uuid_falls_back_after_connection_error():
    client = MojangClient(max_retries=1)
    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {"id": "28667672039044989b0019b14a2c34d6", "name": "Refraction"}

    client._session.get = MagicMock(
        side_effect=[
            requests.ConnectionError("reset"),
            ok,
        ]
    )

    assert client.lookup_uuid("Refraction") == "28667672039044989b0019b14a2c34d6"
    assert client._session.get.call_count == 2


def test_lookup_uuid_returns_none_for_missing_player():
    client = MojangClient(max_retries=1)
    missing = MagicMock()
    missing.status_code = 404

    client._session.get = MagicMock(return_value=missing)
    assert client.lookup_uuid("NoSuchPlayer_xyz") is None


def test_lookup_uuid_raises_when_all_providers_fail():
    client = MojangClient(max_retries=1)
    client._session.get = MagicMock(
        side_effect=requests.ConnectionError("Connection aborted")
    )

    with pytest.raises(HypixelApiError, match="Mojang lookup failed"):
        client.lookup_uuid("Refraction")


def test_profile_collector_hypixel_fallback_when_mojang_fails():
    mojang = MagicMock()
    mojang.lookup_uuid.side_effect = HypixelApiError("Mojang lookup failed")

    hypixel = MagicMock()
    hypixel.get_player_by_username.return_value = {
        "success": True,
        "player": {"uuid": "28667672039044989b0019b14a2c34d6"},
    }

    collector = ProfileCollector(hypixel=hypixel, mojang=mojang)
    assert collector._resolve_uuid("Refraction") == "28667672039044989b0019b14a2c34d6"
