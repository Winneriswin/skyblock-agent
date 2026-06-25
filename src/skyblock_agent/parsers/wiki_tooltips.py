"""Parse Module:Inventory slot/Tooltips Lua table into minetip records."""

from __future__ import annotations

import re
from typing import Any

_WIKI_AMPERSAND = re.compile(r"&&")


def decode_wiki_lua_string(raw: str) -> str:
    """Decode a Lua single-quoted string from the wiki Tooltips module."""
    text = raw.replace("\\'", "'").replace("\\\\", "\\")
    text = _WIKI_AMPERSAND.sub("&", text)
    return text.replace("\\/", "/")


def _read_lua_string(source: str, start: int) -> tuple[str, int]:
    quote = source[start]
    if quote not in ("'", '"'):
        raise ValueError(f"Expected string at {start}, got {source[start:start + 8]!r}")

    parts: list[str] = []
    index = start + 1
    while index < len(source):
        char = source[index]
        if char == "\\" and index + 1 < len(source):
            parts.append(source[index : index + 2])
            index += 2
            continue
        if char == quote:
            return decode_wiki_lua_string("".join(parts)), index + 1
        parts.append(char)
        index += 1
    raise ValueError("Unterminated Lua string")


def _skip_ws(source: str, index: int) -> int:
    while index < len(source) and source[index] in " \t\r\n":
        index += 1
    return index


def _parse_field_value(source: str, index: int) -> tuple[str, int]:
    index = _skip_ws(source, index)
    if index >= len(source):
        raise ValueError("Unexpected end while parsing field value")
    if source[index] in ("'", '"'):
        return _read_lua_string(source, index)
    raise ValueError(f"Unsupported field value at {index}: {source[index:index + 12]!r}")


def _parse_entry_fields(source: str, start: int, end: int) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = start
    while index < end:
        index = _skip_ws(source, index)
        if index >= end:
            break

        name_match = re.match(r"([A-Za-z_]\w*)\s*=", source[index:])
        if not name_match:
            index += 1
            continue

        field_name = name_match.group(1)
        index += name_match.end()
        value, index = _parse_field_value(source, index)
        fields[field_name] = value

        index = _skip_ws(source, index)
        if index < end and source[index] == ",":
            index += 1
    return fields


def _read_table_key(source: str, index: int) -> tuple[str, int]:
    index = _skip_ws(source, index)
    if index < len(source) and source[index] == "[":
        index += 1
        index = _skip_ws(source, index)
    if index >= len(source) or source[index] not in ("'", '"'):
        raise ValueError(f"Expected table key at {index}")
    key, index = _read_lua_string(source, index)
    index = _skip_ws(source, index)
    if index < len(source) and source[index] == "]":
        index += 1
        index = _skip_ws(source, index)
    return key, index


def parse_wiki_tooltips_module(source: str) -> dict[str, dict[str, Any]]:
    """Parse ``Module:Inventory slot/Tooltips`` into ``{display_name: {title, text, ...}}``."""
    text = source.strip()
    body_start = text.find("{")
    if body_start < 0:
        return {}

    records: dict[str, dict[str, Any]] = {}
    index = body_start + 1
    length = len(text)

    while index < length:
        index = _skip_ws(text, index)
        if index >= length or text[index] == "}":
            break

        if text[index] not in ("'", '"', "["):
            index += 1
            continue

        display_name, index = _read_table_key(text, index)
        index = _skip_ws(text, index)
        if index >= length or text[index] != "=":
            continue
        index += 1
        index = _skip_ws(text, index)
        if index >= length or text[index] != "{":
            continue

        depth = 0
        entry_start = index
        while index < length:
            char = text[index]
            if char in ("'", '"'):
                _, index = _read_lua_string(text, index)
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    fields = _parse_entry_fields(text, entry_start + 1, index)
                    title = fields.get("title", "")
                    body = fields.get("text", "")
                    if title or body:
                        records[display_name] = {
                            "name": fields.get("name") or display_name,
                            "title": title,
                            "text": body,
                        }
                    index += 1
                    break
            index += 1

    return records
