"""Import SkyBlock item icons into local cache (run manually via sync-icons)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from skyblock_agent.collectors.icon_client import IconClient
from skyblock_agent.storage import icon_index
from skyblock_agent.storage.icon_index import IconEntry, IconsMeta
from skyblock_agent.storage.item_index import catalog_is_available, load_catalog_items


@dataclass
class IconsImportResult:
    meta: IconsMeta
    manifest_path: Path
    meta_path: Path


class IconsImporter:
    """Download icons for all catalog items. Requires items import first."""

    def __init__(self, client: IconClient | None = None) -> None:
        self.client = client or IconClient()

    def import_icons(
        self,
        *,
        force: bool = False,
        limit: int | None = None,
        delay_seconds: float = 0.05,
    ) -> IconsImportResult:
        if not catalog_is_available():
            raise RuntimeError(
                "Item catalog not imported. Run sync-items.bat or: skyblock-agent items import"
            )

        catalog = load_catalog_items()
        item_ids = sorted(catalog.keys())
        if limit is not None and limit > 0:
            item_ids = item_ids[:limit]

        existing_raw = icon_index.load_manifest()
        entries: dict[str, IconEntry] = _entries_from_manifest(existing_raw) if not force else {}
        downloaded = 0
        skipped = 0
        failed = 0

        icon_index.ICONS_DIR.mkdir(parents=True, exist_ok=True)

        for index, item_id in enumerate(item_ids, start=1):
            key = item_id.upper()
            filename = icon_index.icon_filename(key)
            target = icon_index.ICONS_DIR / filename

            if not force and key in entries and target.is_file():
                skipped += 1
                continue

            material = None
            item = catalog.get(item_id)
            if isinstance(item, dict):
                material = item.get("material")

            result = self.client.fetch_icon(key, material=material)
            if result is None:
                failed += 1
                if delay_seconds:
                    time.sleep(delay_seconds)
                continue

            target.write_bytes(result.data)
            entries[key] = IconEntry(
                item_id=key,
                source=result.source.value,
                source_url=result.source_url,
                filename=filename,
            )
            downloaded += 1

            if delay_seconds:
                time.sleep(delay_seconds)

            if index % 200 == 0:
                print(
                    f"[icons] {index}/{len(item_ids)} "
                    f"(downloaded={downloaded}, skipped={skipped}, failed={failed})"
                )

        imported_at = datetime.now(timezone.utc).isoformat()
        manifest_path, meta_path = icon_index.save_icon_cache(
            entries=entries,
            last_imported_at=imported_at,
            catalog_item_count=len(catalog),
            downloaded=downloaded,
            skipped=skipped,
            failed=failed,
        )

        icon_count = len(entries)
        coverage = (icon_count / len(catalog) * 100.0) if catalog else 0.0
        meta = IconsMeta(
            last_imported_at=imported_at,
            catalog_item_count=len(catalog),
            downloaded=downloaded,
            skipped=skipped,
            failed=failed,
            coverage_pct=round(coverage, 2),
            icon_count=icon_count,
        )
        return IconsImportResult(
            meta=meta,
            manifest_path=manifest_path,
            meta_path=meta_path,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> IconsImporter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _entries_from_manifest(raw: dict[str, dict]) -> dict[str, IconEntry]:
    entries: dict[str, IconEntry] = {}
    for item_id, row in raw.items():
        if not isinstance(row, dict):
            continue
        key = item_id.upper()
        entries[key] = IconEntry(
            item_id=key,
            source=str(row.get("source") or ""),
            source_url=str(row.get("source_url") or ""),
            filename=str(row.get("filename") or icon_index.icon_filename(key)),
        )
    return entries
