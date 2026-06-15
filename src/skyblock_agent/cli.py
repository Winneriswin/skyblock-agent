"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from skyblock_agent.collectors.hypixel_client import HypixelApiError
from skyblock_agent.collectors.player_lookup import PlayerLookupService
from skyblock_agent.serializers import build_lookup_payload, profile_result_to_dict
from skyblock_agent.storage.player_index import list_players
from skyblock_agent.validation.api_recognizer import recognize_player_result


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
        lines.append("Saved files:")
        for path in result.raw_paths:
            lines.append(f"  {path}")

    return "\n".join(lines)


def _format_import_record(record) -> str:
    lines = [
        f"Imported at: {record.last_imported_at}",
        f"Selected profile: {record.selected_profile or '—'}",
        "Saved:",
    ]
    for label, path in record.saved_files.items():
        lines.append(f"  {label}: {path}")
    return "\n".join(lines)


def _format_recognition_report(report) -> str:
    lines = [
        f"Recognition: {report.ok_count}/{report.total_count} fields OK "
        f"({report.pass_rate * 100:.1f}%)",
        f"Required fields OK: {'yes' if report.all_required_ok else 'no'}",
        "",
    ]
    for check in report.checks:
        detail = f" — {check.detail}" if check.detail else ""
        lines.append(f"[{check.status:7}] {check.label}{detail}")
    return "\n".join(lines)


def _run_lookup(args: argparse.Namespace):
    with PlayerLookupService() as service:
        lookup = service.lookup(args.username, profile_name=args.profile)
    report = recognize_player_result(lookup.profile)
    return lookup, report


def cmd_lookup(args: argparse.Namespace) -> int:
    try:
        lookup, report = _run_lookup(args)
    except HypixelApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(build_lookup_payload(lookup, report), indent=2, ensure_ascii=False))
    else:
        print(_format_profile_result(lookup.profile))
        print()
        print(_format_import_record(lookup.import_record))
        if args.recognition:
            print()
            print(_format_recognition_report(report))
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    args.recognition = getattr(args, "recognition", False)
    return cmd_lookup(args)


def cmd_test_api(args: argparse.Namespace) -> int:
    try:
        lookup, report = _run_lookup(args)
    except HypixelApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    payload = build_lookup_payload(lookup, report)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(_format_profile_result(lookup.profile))
        print()
        print(_format_import_record(lookup.import_record))
        print()
        print(_format_recognition_report(report))

    if report.all_required_ok:
        return 0
    return 3


def cmd_list_players(args: argparse.Namespace) -> int:
    records = list_players()
    if args.json:
        print(json.dumps({"players": [r.to_dict() for r in records]}, indent=2))
        return 0

    if not records:
        print("No imported players yet. Use: skyblock-agent lookup <username>")
        return 0

    for record in records:
        profiles = ", ".join(record.profiles) if record.profiles else "—"
        print(f"{record.username} ({record.uuid})")
        print(f"  imported: {record.last_imported_at}")
        print(f"  profiles: {profiles}")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from skyblock_agent.web.app import run
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Skyblock Agent GUI: http://{args.host}:{args.port}")
    run(host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skyblock-agent",
        description="Hypixel SkyBlock info collector",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    lookup = sub.add_parser(
        "lookup",
        help="Look up a player by username and import Hypixel API data locally",
    )
    lookup.add_argument("username", help="Minecraft username")
    lookup.add_argument(
        "--profile",
        "-p",
        help="Profile name (e.g. Apple). Defaults to selected profile.",
    )
    lookup.add_argument("--json", action="store_true")
    lookup.add_argument("--recognition", action="store_true")
    lookup.set_defaults(func=cmd_lookup)

    profile = sub.add_parser("profile", help="Alias for lookup")
    profile.add_argument("username", help="Minecraft username")
    profile.add_argument("--profile", "-p", help="Profile cute name")
    profile.add_argument("--json", action="store_true")
    profile.add_argument("--recognition", action="store_true")
    profile.set_defaults(func=cmd_profile)

    test_api = sub.add_parser(
        "test-api",
        help="Lookup a player and print API field recognition results",
    )
    test_api.add_argument("username", help="Minecraft username")
    test_api.add_argument("--profile", "-p", help="Profile cute name")
    test_api.add_argument("--json", action="store_true")
    test_api.set_defaults(func=cmd_test_api)

    players = sub.add_parser("players", help="List locally imported players")
    players.add_argument("--json", action="store_true")
    players.set_defaults(func=cmd_list_players)

    gui = sub.add_parser("gui", help="Launch the local web UI")
    gui.add_argument("--host", default="127.0.0.1")
    gui.add_argument("--port", type=int, default=8765)
    gui.set_defaults(func=cmd_gui)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
