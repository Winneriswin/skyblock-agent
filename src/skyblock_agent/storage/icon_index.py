"""Local SkyBlock item icon cache (downloaded by sync-icons, not fetched by GUI)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skyblock_agent.config import DATA_DIR

ICONS_DIR = DATA_DIR / "processed" / "items" / "icons"
META_PATH = ICONS_DIR / "meta.json"
MANIFEST_PATH = ICONS_DIR / "manifest.json"

_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class IconEntry:
    item_id: str
    source: str
    source_url: str
    filename: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source": self.source,
            "source_url": self.source_url,
            "filename": self.filename,
        }


@dataclass
class IconsMeta:
    last_imported_at: str
    catalog_item_count: int
    downloaded: int
    skipped: int
    failed: int
    coverage_pct: float
    icon_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_imported_at": self.last_imported_at,
            "catalog_item_count": self.catalog_item_count,
            "downloaded": self.downloaded,
            "skipped": self.skipped,
            "failed": self.failed,
            "coverage_pct": self.coverage_pct,
            "icon_count": self.icon_count,
        }


def icon_filename(item_id: str) -> str:
    safe = _SAFE_ID.sub("_", item_id.strip().upper())
    return f"{safe or 'UNKNOWN'}.png"


def icons_are_available() -> bool:
    return META_PATH.exists() and MANIFEST_PATH.exists()


def load_manifest() -> dict[str, dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        return {}
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, dict):
        return {}
    return items


def get_icons_meta() -> IconsMeta | None:
    if not META_PATH.exists():
        return None
    data = json.loads(META_PATH.read_text(encoding="utf-8"))
    return IconsMeta(
        last_imported_at=str(data.get("last_imported_at", "")),
        catalog_item_count=int(data.get("catalog_item_count") or 0),
        downloaded=int(data.get("downloaded") or 0),
        skipped=int(data.get("skipped") or 0),
        failed=int(data.get("failed") or 0),
        coverage_pct=float(data.get("coverage_pct") or 0.0),
        icon_count=int(data.get("icon_count") or 0),
    )


def has_icon(item_id: str) -> bool:
    entry = load_manifest().get(item_id.strip().upper())
    if not entry:
        return False
    path = ICONS_DIR / str(entry.get("filename") or icon_filename(item_id))
    return path.is_file() and path.stat().st_size >= 64


def get_icon_path(item_id: str) -> Path | None:
    key = item_id.strip().upper()
    entry = load_manifest().get(key)
    if entry:
        path = ICONS_DIR / str(entry.get("filename") or icon_filename(key))
        if path.is_file():
            return path

    fallback = ICONS_DIR / icon_filename(key)
    if fallback.is_file():
        return fallback
    return None


def save_icon_cache(
    *,
    entries: dict[str, IconEntry],
    last_imported_at: str,
    catalog_item_count: int,
    downloaded: int,
    skipped: int,
    failed: int,
) -> tuple[Path, Path]:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    icon_count = len(entries)
    coverage = (icon_count / catalog_item_count * 100.0) if catalog_item_count else 0.0

    manifest = {
        "items": {item_id: entry.to_dict() for item_id, entry in sorted(entries.items())},
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    meta = {
        "last_imported_at": last_imported_at,
        "catalog_item_count": catalog_item_count,
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "coverage_pct": round(coverage, 2),
        "icon_count": icon_count,
    }
    META_PATH.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return MANIFEST_PATH, META_PATH
