"""Tests for Bazaar and Auction House parsing and import."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from skyblock_agent.collectors.market_collector import MarketCollector
from skyblock_agent.models.market import (
    filter_auctions,
    filter_bazaar_products,
    parse_auctions,
    parse_bazaar_products,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_parse_bazaar_products():
    payload = _load("bazaar_sample.json")
    products = parse_bazaar_products(payload)
    assert len(products) == 2
    diamond = next(p for p in products if p.product_id == "ENCHANTED_DIAMOND")
    assert diamond.buy_price == 1100.0
    assert diamond.sell_price == 1200.5
    assert diamond.spread == 100.5


def test_filter_bazaar_products():
    payload = _load("bazaar_sample.json")
    products = parse_bazaar_products(payload)
    matches = filter_bazaar_products(products, "diamond")
    assert len(matches) == 1
    assert matches[0].product_id == "ENCHANTED_DIAMOND"


def test_parse_auctions():
    payload = _load("auctions_page_sample.json")
    auctions = parse_auctions(payload)
    assert len(auctions) == 2
    aod = next(a for a in auctions if "Dragons" in a.item_name)
    assert aod.bin is True
    assert aod.price == 5_000_000
    assert aod.item_id is None


def test_parse_auction_item_id_from_item_bytes():
    from skyblock_agent.models.market import parse_auction

    payload = json.loads(
        Path("data/raw/hypixel_api/auctions/page_0.json").read_text(encoding="utf-8")
    )
    raw = payload["data"]["auctions"][0]
    parsed = parse_auction(raw)
    assert parsed is not None
    assert parsed.item_id == "SNIPER_HELMET"


def test_filter_auctions_bin_only():
    payload = _load("auctions_page_sample.json")
    auctions = parse_auctions(payload)
    bins = filter_auctions(auctions, "", bin_only=True)
    assert len(bins) == 1
    assert bins[0].item_name == "Aspect of the Dragons"


def test_market_collector_saves_bazaar(tmp_path, monkeypatch):
    monkeypatch.setenv("SKYBLOCK_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HYPIXEL_API_KEY", "test-key")

    from skyblock_agent import config

    config.DATA_DIR = tmp_path
    config.RAW_HYPIXEL_DIR = tmp_path / "raw" / "hypixel_api"

    from skyblock_agent.storage import raw_store

    raw_store.RAW_HYPIXEL_DIR = tmp_path / "raw" / "hypixel_api"

    hypixel = MagicMock()
    hypixel.get_bazaar.return_value = _load("bazaar_sample.json")

    with MarketCollector(hypixel=hypixel) as collector:
        snapshot = collector.fetch_bazaar()

    assert snapshot.total_products == 2
    assert snapshot.raw_path.exists()
    saved = json.loads(snapshot.raw_path.read_text(encoding="utf-8"))
    assert saved["data"]["success"] is True


def test_market_collector_filters_auctions_page(tmp_path, monkeypatch):
    monkeypatch.setenv("SKYBLOCK_AGENT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HYPIXEL_API_KEY", "test-key")

    from skyblock_agent import config

    config.DATA_DIR = tmp_path
    config.RAW_HYPIXEL_DIR = tmp_path / "raw" / "hypixel_api"

    from skyblock_agent.storage import raw_store

    raw_store.RAW_HYPIXEL_DIR = tmp_path / "raw" / "hypixel_api"

    hypixel = MagicMock()
    hypixel.get_auctions.return_value = _load("auctions_page_sample.json")

    with MarketCollector(hypixel=hypixel) as collector:
        page = collector.search_auctions_page(0, "diamond", bin_only=False)

    assert page.total_auctions == 1500
    assert len(page.auctions) == 1
    assert page.auctions[0].item_name == "Enchanted Diamond"
