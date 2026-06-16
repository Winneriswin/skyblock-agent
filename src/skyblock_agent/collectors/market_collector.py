"""Fetch and import Hypixel Bazaar and Auction House data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skyblock_agent.collectors.hypixel_client import HypixelClient
from skyblock_agent.models.market import (
    AuctionListing,
    BazaarProduct,
    filter_auctions,
    filter_bazaar_products,
    parse_auctions,
    parse_bazaar_products,
    sort_auctions,
    sort_bazaar_products,
)
from skyblock_agent.storage.item_index import get_catalog_item
from skyblock_agent.storage.raw_store import save_raw_json


@dataclass
class BazaarSnapshotResult:
    last_updated: int
    products: list[BazaarProduct]
    raw_path: Path
    total_products: int


@dataclass
class AuctionsPageResult:
    page: int
    total_pages: int
    total_auctions: int
    last_updated: int
    auctions: list[AuctionListing]
    raw_path: Path


class MarketCollector:
    def __init__(self, hypixel: HypixelClient | None = None) -> None:
        self.hypixel = hypixel or HypixelClient()

    def fetch_bazaar(self, *, save: bool = True) -> BazaarSnapshotResult:
        payload = self.hypixel.get_bazaar()
        raw_path = Path()
        if save:
            raw_path = save_raw_json("bazaar", "snapshot", payload)

        products = parse_bazaar_products(payload)
        return BazaarSnapshotResult(
            last_updated=int(payload.get("lastUpdated") or 0),
            products=products,
            raw_path=raw_path,
            total_products=len(products),
        )

    def fetch_auctions_page(self, page: int = 0, *, save: bool = True) -> AuctionsPageResult:
        payload = self.hypixel.get_auctions(page)
        raw_path = Path()
        if save:
            raw_path = save_raw_json("auctions", f"page_{page}", payload)

        auctions = parse_auctions(payload)
        return AuctionsPageResult(
            page=int(payload.get("page") or page),
            total_pages=int(payload.get("totalPages") or 0),
            total_auctions=int(payload.get("totalAuctions") or 0),
            last_updated=int(payload.get("lastUpdated") or 0),
            auctions=auctions,
            raw_path=raw_path,
        )

    def search_bazaar(
        self,
        query: str = "",
        *,
        category: str = "",
        sort: str = "name",
        save: bool = True,
    ) -> BazaarSnapshotResult:
        snapshot = self.fetch_bazaar(save=save)
        products = snapshot.products
        if query.strip():
            products = self._filter_bazaar_with_catalog(products, query)
        if category.strip():
            products = self._filter_bazaar_category(products, category)
        snapshot.products = sort_bazaar_products(products, sort)
        return snapshot

    def search_auctions_page(
        self,
        page: int = 0,
        query: str = "",
        *,
        bin_only: bool = False,
        category: str = "",
        sort: str = "price",
        save: bool = True,
    ) -> AuctionsPageResult:
        result = self.fetch_auctions_page(page, save=save)
        if query.strip() or bin_only or category.strip():
            result.auctions = filter_auctions(
                result.auctions,
                query,
                bin_only=bin_only,
                category=category,
            )
        result.auctions = sort_auctions(result.auctions, sort)
        return result

    @staticmethod
    def _filter_bazaar_with_catalog(
        products: list[BazaarProduct],
        query: str,
    ) -> list[BazaarProduct]:
        needle = query.strip().lower().replace(" ", "_")
        if not needle:
            return products

        matched: list[BazaarProduct] = []
        for product in products:
            haystack = product.product_id.lower()
            if needle in haystack:
                matched.append(product)
                continue
            item = get_catalog_item(product.product_id)
            if item:
                name = str(item.get("name") or "").lower()
                if needle in name or needle.replace("_", " ") in name:
                    matched.append(product)
        return matched

    @staticmethod
    def _filter_bazaar_category(
        products: list[BazaarProduct],
        category: str,
    ) -> list[BazaarProduct]:
        category_key = category.strip().upper()
        if category_key == "ENCHANTMENT":
            return [p for p in products if p.product_id.startswith("ENCHANTMENT_")]
        if category_key == "OTHER":
            return [
                p
                for p in products
                if get_catalog_item(p.product_id) is None
                and not p.product_id.startswith("ENCHANTMENT_")
            ]

        matched: list[BazaarProduct] = []
        for product in products:
            item = get_catalog_item(product.product_id)
            item_category = str(item.get("category") or "UNKNOWN") if item else None
            if item_category == category_key:
                matched.append(product)
        return matched

    def close(self) -> None:
        self.hypixel.close()

    def __enter__(self) -> MarketCollector:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
