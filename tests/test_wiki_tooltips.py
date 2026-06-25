"""Tests for wiki tooltip Lua parsing."""

from pathlib import Path

from skyblock_agent.parsers.wiki_tooltips import decode_wiki_lua_string, parse_wiki_tooltips_module

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_decode_wiki_lua_string():
    assert decode_wiki_lua_string("&&6Hyperion") == "&6Hyperion"
    assert decode_wiki_lua_string("line1/line2") == "line1/line2"
    assert decode_wiki_lua_string("A Beginner\\'s Guide") == "A Beginner's Guide"


def test_parse_wiki_tooltips_sample():
    source = "return {\n" + (FIXTURES / "wiki_tooltips_sample.lua").read_text(encoding="utf-8") + "\n}"
    records = parse_wiki_tooltips_module(source)
    assert "Hyperion" in records
    assert records["Hyperion"]["title"] == "&6Hyperion"
    assert "Damage" in records["Hyperion"]["text"]

    guide = records["A Beginner's Guide to Pesthunting"]
    assert guide["title"].startswith("&6A Beginner's Guide")
