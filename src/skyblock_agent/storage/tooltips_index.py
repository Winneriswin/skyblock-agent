"""Local item tooltip cache (NEU lore, wiki minetip, Hypixel stats)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skyblock_agent.config import DATA_DIR
from skyblock_agent.parsers.nbt_inventory import strip_color_codes

ITEMS_DIR = DATA_DIR / "processed" / "items"
TOOLTIPS_PATH = ITEMS_DIR / "tooltips.json"
TOOLTIPS_META_PATH = ITEMS_DIR / "tooltips_meta.json"

_tooltips_cache: dict[str, dict[str, Any]] | None = None
_tooltips_mtime: float | None = None


@dataclass
class TooltipsMeta:
    last_imported_at: str
    item_count: int
    sources: dict[str, int]
    raw_paths: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_imported_at": self.last_imported_at,
            "item_count": self.item_count,
            "sources": self.sources,
            "raw_paths": self.raw_paths,
        }


def tooltips_are_available() -> bool:
    return TOOLTIPS_PATH.exists() and TOOLTIPS_META_PATH.exists()


def get_tooltips_meta() -> TooltipsMeta | None:
    if not TOOLTIPS_META_PATH.exists():
        return None
    data = json.loads(TOOLTIPS_META_PATH.read_text(encoding="utf-8"))
    return TooltipsMeta(
        last_imported_at=str(data.get("last_imported_at") or ""),
        item_count=int(data.get("item_count") or 0),
        sources={str(k): int(v) for k, v in (data.get("sources") or {}).items()},
        raw_paths={str(k): str(v) for k, v in (data.get("raw_paths") or {}).items()},
    )


def load_tooltips() -> dict[str, dict[str, Any]]:
    global _tooltips_cache, _tooltips_mtime
    if not TOOLTIPS_PATH.exists():
        return {}
    mtime = TOOLTIPS_PATH.stat().st_mtime
    if _tooltips_cache is not None and _tooltips_mtime == mtime:
        return _tooltips_cache

    data = json.loads(TOOLTIPS_PATH.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, dict):
        items = {}
    _tooltips_cache = items
    _tooltips_mtime = mtime
    return items


def get_item_tooltip(item_id: str) -> dict[str, Any] | None:
    item = load_tooltips().get(item_id)
    return item if isinstance(item, dict) else None


def normalize_lookup_name(name: str) -> str:
    text = strip_color_codes(name.replace("&", "§"))
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def build_name_to_id_map(entries: dict[str, dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item_id, record in entries.items():
        candidates = [item_id.replace("_", " ")]
        title = record.get("title")
        if isinstance(title, str) and title:
            candidates.append(strip_color_codes(title.replace("&", "§")))
        for candidate in candidates:
            key = normalize_lookup_name(candidate)
            if key and key not in mapping:
                mapping[key] = item_id
    return mapping


def save_tooltips(
    *,
    items: dict[str, dict[str, Any]],
    sources: dict[str, int],
    raw_paths: dict[str, str],
) -> tuple[Path, Path]:
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    imported_at = datetime.now(timezone.utc).isoformat()

    TOOLTIPS_PATH.write_text(
        json.dumps({"items": items}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    global _tooltips_cache, _tooltips_mtime
    _tooltips_cache = items
    _tooltips_mtime = TOOLTIPS_PATH.stat().st_mtime

    meta = TooltipsMeta(
        last_imported_at=imported_at,
        item_count=len(items),
        sources=sources,
        raw_paths=raw_paths,
    )
    TOOLTIPS_META_PATH.write_text(
        json.dumps(meta.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return TOOLTIPS_PATH, TOOLTIPS_META_PATH
