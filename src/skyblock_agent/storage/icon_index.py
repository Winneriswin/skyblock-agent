"""Local SkyBlock item icon cache (downloaded by sync-icons, not fetched by GUI)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skyblock_agent.config import DATA_DIR

ICONS_DIR = DATA_DIR / "processed" / "items" / "icons"
VANILLA_ICONS_DIR = ICONS_DIR / "vanilla"
META_PATH = ICONS_DIR / "meta.json"
MANIFEST_PATH = ICONS_DIR / "manifest.json"

_manifest_cache: dict[str, dict[str, Any]] | None = None
_manifest_mtime: float | None = None

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


def vanilla_icon_filename(material: str) -> str:
    from skyblock_agent.collectors.icon_client import _material_slug

    slug = _material_slug(material)
    safe = _SAFE_ID.sub("_", slug or "unknown")
    return f"{safe or 'UNKNOWN'}.png"


def get_vanilla_icon_path(material: str) -> Path | None:
    if not material:
        return None
    path = VANILLA_ICONS_DIR / vanilla_icon_filename(material)
    return path if path.is_file() and path.stat().st_size >= 64 else None


def get_vanilla_icon_path_for_item(item_id: str) -> Path | None:
    from skyblock_agent.storage.item_index import get_catalog_item

    catalog = get_catalog_item(item_id.strip().upper())
    if not catalog:
        return None
    material = catalog.get("material")
    if not isinstance(material, str) or not material.strip():
        return None
    return get_vanilla_icon_path(material)


def ensure_vanilla_icon_for_item(item_id: str, client) -> Path | None:
    """Return cached vanilla icon path, downloading on first request if needed."""
    from skyblock_agent.storage.item_index import get_catalog_item

    key = item_id.strip().upper()
    existing = get_vanilla_icon_path_for_item(key)
    if existing is not None:
        return existing

    catalog = get_catalog_item(key)
    if not catalog:
        return None
    material = catalog.get("material")
    if not isinstance(material, str) or not material.strip():
        return None

    result = client.fetch_vanilla_icon(material)
    if result is None:
        return None

    VANILLA_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    path = VANILLA_ICONS_DIR / vanilla_icon_filename(material)
    path.write_bytes(result.data)
    return path


def icons_are_available() -> bool:
    return META_PATH.exists() and MANIFEST_PATH.exists()


def load_manifest() -> dict[str, dict[str, Any]]:
    global _manifest_cache, _manifest_mtime
    if not MANIFEST_PATH.exists():
        return {}
    mtime = MANIFEST_PATH.stat().st_mtime
    if _manifest_cache is not None and _manifest_mtime == mtime:
        return _manifest_cache

    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, dict):
        items = {}
    _manifest_cache = items
    _manifest_mtime = mtime
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
    global _manifest_cache, _manifest_mtime
    _manifest_cache = manifest["items"]
    _manifest_mtime = MANIFEST_PATH.stat().st_mtime

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
