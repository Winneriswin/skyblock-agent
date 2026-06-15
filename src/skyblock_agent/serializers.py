"""Serialize profile results for CLI, API, and GUI."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from skyblock_agent.storage.player_index import PlayerImportRecord
from skyblock_agent.collectors.player_lookup import LookupResult
from skyblock_agent.validation.api_recognizer import RecognitionReport


def profile_result_to_dict(result) -> dict[str, Any]:
    summary = result.summary
    return {
        "username": result.username,
        "uuid": result.uuid,
        "available_profiles": result.available_profiles,
        "summary": {
            "cute_name": summary.cute_name,
            "profile_id": summary.profile_id,
            "selected": summary.selected,
            "game_mode": summary.game_mode,
            "skyblock_level": summary.skyblock_level,
            "skills_api_enabled": summary.skills_api_enabled,
            "skills": [asdict(skill) for skill in summary.skills],
            "slayers": [asdict(slayer) for slayer in summary.slayers],
            "catacombs_level": summary.catacombs_level,
            "member_count": summary.member_count,
        },
        "raw_paths": result.raw_paths,
    }


def import_record_to_dict(record: PlayerImportRecord) -> dict[str, Any]:
    return record.to_dict()


def build_api_payload(
    lookup: LookupResult,
    report: RecognitionReport,
) -> dict[str, Any]:
    return {
        "profile": profile_result_to_dict(lookup.profile),
        "import": import_record_to_dict(lookup.import_record),
        "recognition": report.to_dict(),
    }


def build_lookup_payload(lookup: LookupResult, report: RecognitionReport) -> dict[str, Any]:
    return build_api_payload(lookup, report)
