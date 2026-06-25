"""Parse Hypixel Bazaar and Auction House API payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BazaarProduct:
    product_id: str
    buy_price: float
    sell_price: float
    buy_volume: int
    sell_volume: int
    buy_orders: int
    sell_orders: int
    buy_moving_week: int
    sell_moving_week: int

    @property
    def spread(self) -> float:
        """Instant-buy minus instant-sell price (coins per unit)."""
        return self.sell_price - self.buy_price

    @property
    def spread_pct(self) -> float | None:
        if self.buy_price <= 0:
            return None
        return (self.spread / self.buy_price) * 100.0


@dataclass(frozen=True)
class AuctionListing:
    uuid: str
    item_name: str
    tier: str
    category: str
    bin: bool
    starting_bid: int
    highest_bid_amount: int
    end: int
    item_lore: str
    item_id: str | None = None

    @property
    def price(self) -> int:
        if self.bin:
            return self.starting_bid
        if self.highest_bid_amount > 0:
            return self.highest_bid_amount
        return self.starting_bid


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_bazaar_product(product_id: str, raw: dict[str, Any]) -> BazaarProduct | None:
    if not isinstance(raw, dict):
        return None

    quick = raw.get("quick_status")
    if not isinstance(quick, dict):
        return None

    return BazaarProduct(
        product_id=str(raw.get("product_id") or product_id),
        buy_price=_float(quick.get("buyPrice")),
        sell_price=_float(quick.get("sellPrice")),
        buy_volume=_int(quick.get("buyVolume")),
        sell_volume=_int(quick.get("sellVolume")),
        buy_orders=_int(quick.get("buyOrders")),
        sell_orders=_int(quick.get("sellOrders")),
        buy_moving_week=_int(quick.get("buyMovingWeek")),
        sell_moving_week=_int(quick.get("sellMovingWeek")),
    )


def parse_bazaar_products(payload: dict[str, Any]) -> list[BazaarProduct]:
    products_root = payload.get("products")
    if not isinstance(products_root, dict):
        return []

    products: list[BazaarProduct] = []
    for product_id, raw in products_root.items():
        parsed = parse_bazaar_product(str(product_id), raw)
        if parsed is not None:
            products.append(parsed)
    products.sort(key=lambda item: item.product_id)
    return products


def _parse_auction_item_id(raw: dict[str, Any]) -> str | None:
    item_bytes = raw.get("item_bytes")
    if not item_bytes:
        return None
    try:
        from skyblock_agent.parsers.nbt_inventory import parse_inventory_blob

        stacks = parse_inventory_blob(item_bytes)
        if stacks and stacks[0].item_id:
            return stacks[0].item_id
    except Exception:
        return None
    return None


def parse_auction(raw: dict[str, Any]) -> AuctionListing | None:
    if not isinstance(raw, dict):
        return None

    uuid = str(raw.get("uuid") or "")
    if not uuid:
        return None

    return AuctionListing(
        uuid=uuid,
        item_name=str(raw.get("item_name") or "Unknown"),
        tier=str(raw.get("tier") or ""),
        category=str(raw.get("category") or ""),
        bin=bool(raw.get("bin")),
        starting_bid=_int(raw.get("starting_bid")),
        highest_bid_amount=_int(raw.get("highest_bid_amount")),
        end=_int(raw.get("end")),
        item_lore=str(raw.get("item_lore") or ""),
        item_id=_parse_auction_item_id(raw),
    )


def parse_auctions(payload: dict[str, Any]) -> list[AuctionListing]:
    auctions_root = payload.get("auctions")
    if not isinstance(auctions_root, list):
        return []

    auctions: list[AuctionListing] = []
    for raw in auctions_root:
        parsed = parse_auction(raw)
        if parsed is not None:
            auctions.append(parsed)
    return auctions


def filter_bazaar_products(
    products: list[BazaarProduct],
    query: str,
) -> list[BazaarProduct]:
    needle = query.strip().lower().replace(" ", "_")
    if not needle:
        return products
    return [product for product in products if needle in product.product_id.lower()]


def filter_auctions(
    auctions: list[AuctionListing],
    query: str,
    *,
    bin_only: bool = False,
    category: str = "",
) -> list[AuctionListing]:
    filtered = auctions
    if bin_only:
        filtered = [auction for auction in filtered if auction.bin]

    category_key = category.strip().lower()
    if category_key:
        filtered = [
            auction for auction in filtered if auction.category.lower() == category_key
        ]

    needle = query.strip().lower()
    if not needle:
        return filtered

    return [
        auction
        for auction in filtered
        if needle in auction.item_name.lower()
        or needle in auction.tier.lower()
        or needle in auction.category.lower()
    ]


def sort_bazaar_products(
    products: list[BazaarProduct],
    sort: str,
) -> list[BazaarProduct]:
    key = sort.strip().lower()
    if key == "sell":
        return sorted(products, key=lambda item: item.sell_price, reverse=True)
    if key == "buy":
        return sorted(products, key=lambda item: item.buy_price, reverse=True)
    if key == "spread":
        return sorted(products, key=lambda item: item.spread, reverse=True)
    return sorted(products, key=lambda item: item.product_id)


def sort_auctions(auctions: list[AuctionListing], sort: str) -> list[AuctionListing]:
    key = sort.strip().lower()
    if key == "price":
        return sorted(auctions, key=lambda item: item.price, reverse=True)
    if key == "name":
        return sorted(auctions, key=lambda item: item.item_name.lower())
    if key == "tier":
        return sorted(auctions, key=lambda item: item.tier)
    return auctions


AH_CATEGORIES = ("armor", "weapon", "accessories", "misc", "consumables", "cosmetic", "dyes")
