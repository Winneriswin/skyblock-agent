"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from skyblock_agent.collectors.hypixel_client import HypixelApiError
from skyblock_agent.collectors.icons_importer import IconsImporter
from skyblock_agent.collectors.items_importer import ItemsImporter
from skyblock_agent.collectors.tooltips_importer import TooltipsImporter
from skyblock_agent.collectors.market_collector import MarketCollector
from skyblock_agent.collectors.player_lookup import PlayerLookupService
from skyblock_agent.serializers import (
    build_auctions_payload,
    build_bazaar_payload,
    build_lookup_payload,
    profile_result_to_dict,
)
from skyblock_agent.storage.icon_index import get_icons_meta, has_icon, icons_are_available
from skyblock_agent.storage.item_index import catalog_is_available, get_catalog_meta, search_items
from skyblock_agent.storage.tooltips_index import get_tooltips_meta, tooltips_are_available
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
    import threading
    import time
    import urllib.error
    import urllib.request
    import webbrowser

    try:
        from skyblock_agent.web.app import run
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    base = f"http://{args.host}:{args.port}"
    health_url = f"{base}/api/health"

    def _open_browser_when_ready() -> None:
        for _ in range(60):
            try:
                urllib.request.urlopen(health_url, timeout=1)
                time.sleep(0.4)
                with urllib.request.urlopen(f"{base}/", timeout=2) as response:
                    html = response.read().decode("utf-8", errors="replace")
                if 'data-view="market"' not in html:
                    time.sleep(0.25)
                    continue
                webbrowser.open(f"{base}/?v={int(time.time())}")
                return
            except (urllib.error.URLError, OSError):
                time.sleep(0.25)

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()
    print(f"Skyblock Agent GUI: {base}")
    print(f"[gui] log_level={args.log_level}")
    run(host=args.host, port=args.port, log_level=args.log_level)
    return 0


def _format_bazaar(snapshot, *, query: str = "", limit: int = 20) -> str:
    products = snapshot.products[:limit]
    lines = [
        f"Bazaar snapshot ({snapshot.total_products} products)",
        f"Last updated: {snapshot.last_updated}",
    ]
    if query:
        lines.append(f"Filter: {query!r} ({len(snapshot.products)} matches)")
    if snapshot.raw_path:
        lines.append(f"Saved: {snapshot.raw_path}")
    lines.append("")
    if not products:
        lines.append("No products matched.")
        return "\n".join(lines)

    lines.append(f"{'Product':<28} {'Buy':>10} {'Sell':>10} {'Spread':>10}")
    for product in products:
        lines.append(
            f"{product.product_id:<28} "
            f"{product.buy_price:>10.2f} "
            f"{product.sell_price:>10.2f} "
            f"{product.spread:>10.2f}"
        )
    if len(snapshot.products) > limit:
        lines.append(f"... and {len(snapshot.products) - limit} more")
    return "\n".join(lines)


def _format_auctions(page, *, query: str = "", bin_only: bool = False, limit: int = 20) -> str:
    auctions = page.auctions[:limit]
    lines = [
        f"Auction House page {page.page + 1}/{page.total_pages} "
        f"({page.total_auctions:,} active auctions)",
        f"Last updated: {page.last_updated}",
    ]
    if query:
        lines.append(f"Filter: {query!r}")
    if bin_only:
        lines.append("BIN only: yes")
    lines.append(f"Matches on this page: {len(page.auctions)}")
    if page.raw_path:
        lines.append(f"Saved: {page.raw_path}")
    lines.append("")
    if not auctions:
        lines.append("No auctions matched on this page.")
        return "\n".join(lines)

    lines.append(f"{'Item':<32} {'Type':>4} {'Price':>12} {'Tier':<10}")
    for auction in auctions:
        kind = "BIN" if auction.bin else "Bid"
        lines.append(
            f"{auction.item_name[:32]:<32} {kind:>4} {auction.price:>12,} {auction.tier:<10}"
        )
    if len(page.auctions) > limit:
        lines.append(f"... and {len(page.auctions) - limit} more on this page")
    return "\n".join(lines)


def cmd_bazaar(args: argparse.Namespace) -> int:
    try:
        with MarketCollector() as collector:
            snapshot = collector.search_bazaar(args.search or "", save=not args.no_save)
    except HypixelApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(build_bazaar_payload(snapshot, query=args.search or "", limit=args.limit), indent=2))
    else:
        print(_format_bazaar(snapshot, query=args.search or "", limit=args.limit))
    return 0


def cmd_auctions(args: argparse.Namespace) -> int:
    try:
        with MarketCollector() as collector:
            page = collector.search_auctions_page(
                args.page,
                args.search or "",
                bin_only=args.bin,
                save=not args.no_save,
            )
    except HypixelApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                build_auctions_payload(
                    page,
                    query=args.search or "",
                    bin_only=args.bin,
                    limit=args.limit,
                ),
                indent=2,
            )
        )
    else:
        print(_format_auctions(page, query=args.search or "", bin_only=args.bin, limit=args.limit))
    return 0


def cmd_items_import(args: argparse.Namespace) -> int:
    try:
        with ItemsImporter() as importer:
            result = importer.import_items(save_raw=not args.no_save)
    except HypixelApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    meta = result.meta
    if args.json:
        print(
            json.dumps(
                {
                    "meta": meta.to_dict(),
                    "catalog_path": str(result.catalog_path),
                    "meta_path": str(result.meta_path),
                },
                indent=2,
            )
        )
    else:
        print(f"Imported {meta.item_count} items in {meta.category_count} categories")
        print(f"Hypixel lastUpdated: {meta.last_updated}")
        print(f"Catalog: {result.catalog_path}")
        print(f"Meta: {result.meta_path}")
        if meta.raw_path:
            print(f"Raw: {meta.raw_path}")
    return 0


def cmd_items_status(args: argparse.Namespace) -> int:
    if not catalog_is_available():
        print("Item catalog: not imported")
        print("Run: skyblock-agent items import  (or sync-items.bat)")
        return 1

    meta = get_catalog_meta()
    if meta is None:
        print("Item catalog: meta file unreadable")
        return 1

    if args.json:
        print(json.dumps({"available": True, "meta": meta.to_dict()}, indent=2))
    else:
        print(f"Item catalog: {meta.item_count} items, {meta.category_count} categories")
        print(f"Imported at: {meta.last_imported_at}")
        print(f"Hypixel lastUpdated: {meta.last_updated}")
    return 0


def cmd_items_search(args: argparse.Namespace) -> int:
    if not catalog_is_available():
        print("Item catalog not imported. Run: skyblock-agent items import", file=sys.stderr)
        return 2

    matches = search_items(args.query or "", category=args.category, limit=args.limit)
    if args.json:
        print(json.dumps({"items": matches, "count": len(matches)}, indent=2, ensure_ascii=False))
        return 0

    if not matches:
        print("No items matched.")
        return 0

    for item in matches:
        category = item.get("category") or "—"
        tier = item.get("tier") or "—"
        icon_flag = "icon" if has_icon(str(item.get("id") or "")) else "no-icon"
        print(f"{item.get('name')} [{item.get('id')}] · {category} · {tier} · {icon_flag}")
    return 0


def cmd_items_tooltips_import(args: argparse.Namespace) -> int:
    sources = tuple(part.strip() for part in args.sources.split(",") if part.strip())
    try:
        with TooltipsImporter() as importer:
            result = importer.import_tooltips(sources=sources, save_raw=not args.no_save)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "item_count": result.item_count,
                    "sources": result.sources,
                    "tooltips_path": str(result.tooltips_path),
                    "meta_path": str(result.meta_path),
                },
                indent=2,
            )
        )
    else:
        print(f"Imported {result.item_count} item tooltips")
        for source, count in sorted(result.sources.items()):
            print(f"  {source}: {count} records merged")
        print(f"Tooltips: {result.tooltips_path}")
        print(f"Meta: {result.meta_path}")
    return 0


def cmd_items_tooltips_status(args: argparse.Namespace) -> int:
    if not tooltips_are_available():
        print("Item tooltips: not imported")
        print("Run: skyblock-agent items tooltips import  (or sync-tooltips.bat)")
        return 1

    meta = get_tooltips_meta()
    if meta is None:
        print("Item tooltips: meta file unreadable")
        return 1

    if args.json:
        print(json.dumps({"available": True, "meta": meta.to_dict()}, indent=2))
    else:
        print(f"Item tooltips: {meta.item_count} items")
        print(f"Imported at: {meta.last_imported_at}")
        for source, count in sorted(meta.sources.items()):
            print(f"  {source}: {count}")
    return 0


def cmd_items_icons_import(args: argparse.Namespace) -> int:
    try:
        with IconsImporter() as importer:
            result = importer.import_icons(
                force=args.force,
                limit=args.limit if args.limit > 0 else None,
                delay_seconds=0.0 if args.fast else 0.05,
            )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    meta = result.meta
    if args.json:
        print(
            json.dumps(
                {
                    "meta": meta.to_dict(),
                    "manifest_path": str(result.manifest_path),
                    "meta_path": str(result.meta_path),
                },
                indent=2,
            )
        )
    else:
        print(
            f"Icons: {meta.downloaded} downloaded, {meta.skipped} skipped, "
            f"{meta.failed} failed ({meta.coverage_pct:.1f}% catalog coverage)"
        )
        print(f"Manifest: {result.manifest_path}")
        print(f"Meta: {result.meta_path}")
    return 0


def cmd_items_icons_status(args: argparse.Namespace) -> int:
    if not icons_are_available():
        print("Item icons: not imported")
        print("Run: skyblock-agent items icons import  (or sync-icons.bat)")
        return 1

    meta = get_icons_meta()
    if meta is None:
        print("Item icons: meta file unreadable")
        return 1

    if args.json:
        print(json.dumps({"available": True, "meta": meta.to_dict()}, indent=2))
    else:
        print(
            f"Item icons: {meta.icon_count} cached "
            f"({meta.coverage_pct:.1f}% of {meta.catalog_item_count} catalog items)"
        )
        print(f"Last sync: {meta.last_imported_at}")
        print(f"Last run: {meta.downloaded} new, {meta.skipped} skipped, {meta.failed} failed")
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
    gui.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level (default: info)",
    )
    gui.set_defaults(func=cmd_gui)

    bazaar = sub.add_parser("bazaar", help="Fetch Bazaar prices and save a local snapshot")
    bazaar.add_argument("--search", "-s", help="Filter by product id (e.g. ENCHANTED_DIAMOND)")
    bazaar.add_argument("--limit", type=int, default=20, help="Rows to print (default: 20)")
    bazaar.add_argument("--json", action="store_true")
    bazaar.add_argument("--no-save", action="store_true", help="Skip writing raw JSON to data/")
    bazaar.set_defaults(func=cmd_bazaar)

    auctions = sub.add_parser("auctions", help="Fetch Auction House page and prices")
    auctions.add_argument("--page", type=int, default=0, help="Auction page index (0-based)")
    auctions.add_argument("--search", "-s", help="Filter item name/tier/category on this page")
    auctions.add_argument("--bin", action="store_true", help="Show buy-it-now listings only")
    auctions.add_argument("--limit", type=int, default=20, help="Rows to print (default: 20)")
    auctions.add_argument("--json", action="store_true")
    auctions.add_argument("--no-save", action="store_true", help="Skip writing raw JSON to data/")
    auctions.set_defaults(func=cmd_auctions)

    items = sub.add_parser("items", help="SkyBlock item catalog (static resources, manual sync)")
    items_sub = items.add_subparsers(dest="items_command", required=True)

    items_import = items_sub.add_parser(
        "import",
        help="Download latest items from Hypixel resources (not run on GUI startup)",
    )
    items_import.add_argument("--json", action="store_true")
    items_import.add_argument("--no-save", action="store_true", help="Skip writing raw JSON to data/")
    items_import.set_defaults(func=cmd_items_import)

    items_status = items_sub.add_parser("status", help="Show local item catalog status")
    items_status.add_argument("--json", action="store_true")
    items_status.set_defaults(func=cmd_items_status)

    items_search = items_sub.add_parser("search", help="Search locally imported items")
    items_search.add_argument("query", nargs="?", default="", help="Name or item id")
    items_search.add_argument("--category", "-c", help="Filter by category (e.g. SWORD)")
    items_search.add_argument("--limit", type=int, default=20)
    items_search.add_argument("--json", action="store_true")
    items_search.set_defaults(func=cmd_items_search)

    items_icons = items_sub.add_parser("icons", help="Item icon cache (manual sync)")
    items_icons_sub = items_icons.add_subparsers(dest="icons_command", required=True)

    icons_import = items_icons_sub.add_parser(
        "import",
        help="Download item icons to data/processed/items/icons/",
    )
    icons_import.add_argument("--force", action="store_true", help="Re-download all icons")
    icons_import.add_argument("--limit", type=int, default=0, help="Max items (0 = all)")
    icons_import.add_argument("--fast", action="store_true", help="Skip delay between downloads")
    icons_import.add_argument("--json", action="store_true")
    icons_import.set_defaults(func=cmd_items_icons_import)

    icons_status = items_icons_sub.add_parser("status", help="Show local icon cache status")
    icons_status.add_argument("--json", action="store_true")
    icons_status.set_defaults(func=cmd_items_icons_status)

    items_tooltips = items_sub.add_parser("tooltips", help="Item tooltip cache (NEU + wiki + Hypixel)")
    tooltips_sub = items_tooltips.add_subparsers(dest="tooltips_command", required=True)

    tooltips_import = tooltips_sub.add_parser(
        "import",
        help="Download tooltips from NEU repo, SkyBlock wiki, and Hypixel stats",
    )
    tooltips_import.add_argument(
        "--sources",
        default="neu,wiki,hypixel",
        help="Comma-separated sources: neu, wiki, hypixel (default: all)",
    )
    tooltips_import.add_argument("--json", action="store_true")
    tooltips_import.add_argument("--no-save", action="store_true", help="Skip writing raw dumps to data/")
    tooltips_import.set_defaults(func=cmd_items_tooltips_import)

    tooltips_status = tooltips_sub.add_parser("status", help="Show local tooltip cache status")
    tooltips_status.add_argument("--json", action="store_true")
    tooltips_status.set_defaults(func=cmd_items_tooltips_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
