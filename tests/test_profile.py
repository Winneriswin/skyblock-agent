"""Tests for profile parsing (no API key required)."""

from skyblock_agent.models.profile import (
    list_player_profiles,
    select_profile,
    skills_api_enabled,
    skyblock_level,
    summarize_profile,
)


def test_select_profile_by_name():
    uuid = "28667672039044989b0019b14a2c34d6"
    response = {
        "success": True,
        "profiles": [
            {
                "cute_name": "Apple",
                "profile_id": "aaa",
                "selected": False,
                "members": {
                    uuid: {
                        "leveling": {"experience": 4200},
                        "player_data": {"experience": {"SKILL_COMBAT": 100}},
                    }
                },
            },
            {
                "cute_name": "Banana",
                "profile_id": "bbb",
                "selected": True,
                "members": {
                    uuid: {
                        "leveling": {"experience": 9000},
                        "player_data": {"experience": {"SKILL_COMBAT": 200}},
                    }
                },
            },
        ],
    }

    profiles = list_player_profiles(response, uuid)
    assert len(profiles) == 2

    selected = select_profile(response, uuid, "Apple")
    assert selected is not None
    assert selected["cute_name"] == "Apple"

    default = select_profile(response, uuid)
    assert default is not None
    assert default["cute_name"] == "Banana"


def test_skills_api_disabled():
    member = {"player_data": {"experience": {"SKILL_COMBAT": -1}}}
    assert skills_api_enabled(member) is False


def test_skyblock_level():
    member = {"leveling": {"experience": 12345}}
    assert skyblock_level(member) == 123.45


def test_summarize_profile():
    uuid = "28667672039044989b0019b14a2c34d6"
    profile = {
        "cute_name": "Kiwi",
        "profile_id": "pid-1",
        "selected": True,
        "game_mode": "ironman",
        "members": {
            uuid: {
                "leveling": {"experience": 5000},
                "player_data": {"experience": {"SKILL_COMBAT": 1000, "SKILL_MINING": 500}},
                "slayer": {
                    "slayer_bosses": {
                        "zombie": {"xp": 10000, "claimed_residents": {"level": 3}},
                    }
                },
            },
            "other-uuid": {},
        },
    }
    summary = summarize_profile(profile, uuid)
    assert summary.cute_name == "Kiwi"
    assert summary.skyblock_level == 50.0
    assert summary.skills_api_enabled is True
    assert summary.member_count == 2
    assert any(s.name == "combat" and s.experience == 1000 for s in summary.skills)


def test_v2_slayer_claimed_levels():
    uuid = "28667672039044989b0019b14a2c34d6"
    profile = {
        "cute_name": "Kiwi",
        "profile_id": "pid-1",
        "selected": True,
        "members": {
            uuid: {
                "slayer": {
                    "slayer_bosses": {
                        "zombie": {
                            "xp": 10000,
                            "claimed_levels": {"1": True, "2": True, "3": True},
                        },
                    }
                },
            }
        },
    }
    summary = summarize_profile(profile, uuid)
    zombie = next(s for s in summary.slayers if s.name == "zombie")
    assert zombie.level == 3
    assert zombie.xp == 10000
