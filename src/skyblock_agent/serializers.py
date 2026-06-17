"""Serialize profile results for CLI, API, and GUI."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from skyblock_agent.collectors.market_collector import AuctionsPageResult, BazaarSnapshotResult
from skyblock_agent.models.market import AH_CATEGORIES
from skyblock_agent.storage.icon_index import has_icon
from skyblock_agent.storage.item_index import get_catalog_item
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


def bazaar_product_to_dict(product) -> dict[str, Any]:
    catalog = get_catalog_item(product.product_id)
    display_name = str(catalog.get("name") or product.product_id.replace("_", " ")) if catalog else product.product_id.replace("_", " ")
    return {
        "product_id": product.product_id,
        "display_name": display_name,
        "category": catalog.get("category") if catalog else None,
        "tier": catalog.get("tier") if catalog else None,
        "has_icon": has_icon(product.product_id),
        "buy_price": product.buy_price,
        "sell_price": product.sell_price,
        "spread": product.spread,
        "spread_pct": product.spread_pct,
        "buy_volume": product.buy_volume,
        "sell_volume": product.sell_volume,
        "buy_orders": product.buy_orders,
        "sell_orders": product.sell_orders,
        "buy_moving_week": product.buy_moving_week,
        "sell_moving_week": product.sell_moving_week,
    }


def auction_to_dict(auction) -> dict[str, Any]:
    return {
        "uuid": auction.uuid,
        "item_name": auction.item_name,
        "tier": auction.tier,
        "category": auction.category,
        "bin": auction.bin,
        "price": auction.price,
        "starting_bid": auction.starting_bid,
        "highest_bid_amount": auction.highest_bid_amount,
        "end": auction.end,
        "item_lore": auction.item_lore,
    }


def build_bazaar_payload(
    snapshot: BazaarSnapshotResult,
    *,
    query: str = "",
    category: str = "",
    sort: str = "name",
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any]:
    matched = snapshot.products
    total_matched = len(matched)
    if offset > 0:
        matched = matched[offset:]
    if limit is not None and limit > 0:
        page_items = matched[:limit]
    else:
        page_items = matched

    return {
        "last_updated": snapshot.last_updated,
        "total_products": snapshot.total_products,
        "matched_products": total_matched,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(page_items) < total_matched,
        "query": query or None,
        "category": category or None,
        "sort": sort,
        "raw_path": str(snapshot.raw_path) if snapshot.raw_path else None,
        "products": [bazaar_product_to_dict(product) for product in page_items],
    }


def build_auctions_payload(
    page: AuctionsPageResult,
    *,
    query: str = "",
    bin_only: bool = False,
    category: str = "",
    sort: str = "price",
    limit: int | None = None,
) -> dict[str, Any]:
    auctions = page.auctions
    if limit is not None and limit > 0:
        auctions = auctions[:limit]

    return {
        "page": page.page,
        "total_pages": page.total_pages,
        "total_auctions": page.total_auctions,
        "last_updated": page.last_updated,
        "matched_auctions": len(page.auctions),
        "page_auctions": len(page.auctions),
        "query": query or None,
        "bin_only": bin_only,
        "category": category or None,
        "sort": sort,
        "categories": list(AH_CATEGORIES),
        "raw_path": str(page.raw_path) if page.raw_path else None,
        "auctions": [auction_to_dict(auction) for auction in auctions],
    }
