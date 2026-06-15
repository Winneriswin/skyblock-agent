"""Tests for API field recognition."""

import json
from pathlib import Path

from skyblock_agent.models.profile import summarize_profile
from skyblock_agent.validation.api_recognizer import recognize_profile_member

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_recognize_v2_profile_fixture():
    payload = _load("profile_v2_sample.json")
    uuid = "28667672039044989b0019b14a2c34d6"
    profile = payload["profiles"][0]

    report = recognize_profile_member(
        username="SamplePlayer",
        uuid="28667672-0390-4498-9b00-19b14a2c34d6",
        profile=profile,
        player_uuid=uuid,
    )

    assert report.all_required_ok
    assert report.ok_count >= 10
    assert any(check.path.endswith("SKILL_COMBAT") and check.status == "ok" for check in report.checks)
    assert any(check.path.endswith("zombie") and check.status == "ok" for check in report.checks)


def test_recognize_dashed_uuid_members():
    payload = _load("profile_v2_dashed_uuid.json")
    uuid = "28667672039044989b0019b14a2c34d6"
    profile = payload["profiles"][0]

    summary = summarize_profile(profile, uuid)
    assert summary.skyblock_level == 42.0
    assert summary.skills_api_enabled is True


def test_hidden_skills_marked():
    payload = _load("profile_api_hidden.json")
    uuid = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    profile = payload["profiles"][0]

    report = recognize_profile_member(
        username="HiddenPlayer",
        uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        profile=profile,
        player_uuid=uuid,
    )

    skills_root = next(c for c in report.checks if c.path == "member.player_data.experience")
    assert skills_root.status == "hidden"
    combat = next(c for c in report.checks if c.path.endswith("SKILL_COMBAT"))
    assert combat.status == "hidden"
