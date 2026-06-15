"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from skyblock_agent.collectors.hypixel_client import HypixelApiError
from skyblock_agent.collectors.profile_collector import ProfileCollector


def _format_profile_result(result) -> str:
    s = result.summary
    lines = [
        f"Player: {result.username}",
        f"UUID: {result.uuid}",
        f"Profile: {s.cute_name} ({s.profile_id})",
        f"Selected: {'yes' if s.selected else 'no'}",
        f"Game mode: {s.game_mode or 'normal'}",
        f"Coop members: {s.member_count}",
        f"SkyBlock level: {s.skyblock_level:.2f}" if s.skyblock_level is not None else "SkyBlock level: (unknown)",
        f"Profiles: {', '.join(result.available_profiles)}",
    ]

    if s.skills_api_enabled:
        lines.append("Skills (API enabled):")
        for skill in s.skills:
            if skill.experience is not None:
                lines.append(f"  {skill.name:12} {skill.experience:,.0f} XP")
    else:
        lines.append("Skills: API disabled in-game (player_data hidden)")

    if s.slayers:
        lines.append("Slayers:")
        for slayer in s.slayers:
            if slayer.xp > 0 or slayer.level > 0:
                lines.append(f"  {slayer.name:10} L{slayer.level}  {slayer.xp:,.0f} XP")

    if s.catacombs_level is not None:
        lines.append(f"Catacombs (raw XP/100): {s.catacombs_level:.2f}")

    if result.raw_paths:
        lines.append(f"Saved: {result.raw_paths[0]}")

    return "\n".join(lines)


def cmd_profile(args: argparse.Namespace) -> int:
    try:
        with ProfileCollector() as collector:
            result = collector.fetch_by_username(
                args.username,
                profile_name=args.profile,
            )
    except HypixelApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        output = {
            "username": result.username,
            "uuid": result.uuid,
            "available_profiles": result.available_profiles,
            "summary": {
                "cute_name": result.summary.cute_name,
                "profile_id": result.summary.profile_id,
                "selected": result.summary.selected,
                "game_mode": result.summary.game_mode,
                "skyblock_level": result.summary.skyblock_level,
                "skills_api_enabled": result.summary.skills_api_enabled,
                "skills": [
                    {"name": sk.name, "experience": sk.experience}
                    for sk in result.summary.skills
                ],
                "slayers": [
                    {"name": sl.name, "level": sl.level, "xp": sl.xp}
                    for sl in result.summary.slayers
                ],
                "catacombs_level": result.summary.catacombs_level,
                "member_count": result.summary.member_count,
            },
            "raw_paths": result.raw_paths,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(_format_profile_result(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skyblock-agent",
        description="Hypixel SkyBlock info collector",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    profile = sub.add_parser("profile", help="Look up a player's SkyBlock profile")
    profile.add_argument("username", help="Minecraft username")
    profile.add_argument(
        "--profile",
        "-p",
        help="Profile name (e.g. Apple). Defaults to selected profile.",
    )
    profile.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of text",
    )
    profile.set_defaults(func=cmd_profile)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
