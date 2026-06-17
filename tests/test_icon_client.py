"""Tests for icon client helpers."""

from skyblock_agent.collectors.icon_client import PNG_MAGIC, _looks_like_png, _material_slug


def test_material_slug():
    assert _material_slug("DIAMOND_SWORD") == "diamond_sword"
    assert _material_slug("minecraft:diamond") == "diamond"


def test_looks_like_png():
    data = PNG_MAGIC + b"x" * 80
    assert _looks_like_png(data, "image/png") is True
    assert _looks_like_png(b"not-a-png", "text/html") is False
