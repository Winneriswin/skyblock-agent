"""Download NotEnoughUpdates item lore files from GitHub."""

from __future__ import annotations

import io
import json
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

NEU_REPO_ZIP_URL = (
    "https://codeload.github.com/NotEnoughUpdates/NotEnoughUpdates-REPO/zip/refs/heads/master"
)


@dataclass
class NeuImportResult:
    item_count: int
    zip_path: Path
    items_dir: Path


class NeuItemsImporter:
    """Fetch NEU-REPO ``items/*.json`` (internalname + lore) into local storage."""

    def __init__(self, *, timeout: float = 300.0, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/zip, application/octet-stream",
                "User-Agent": "skyblock-agent/0.1.0 (tooltip sync)",
            }
        )

    def import_items(self, *, raw_dir: Path, extract: bool = True) -> NeuImportResult:
        raw_dir.mkdir(parents=True, exist_ok=True)
        zip_path = raw_dir / "neu_repo.zip"
        items_dir = raw_dir / "neu" / "items"

        payload = self._download_zip()
        zip_path.write_bytes(payload)

        item_count = 0
        if extract:
            items_dir.mkdir(parents=True, exist_ok=True)
            item_count = self._extract_items(payload, items_dir)

        return NeuImportResult(item_count=item_count, zip_path=zip_path, items_dir=items_dir)

    def _download_zip(self) -> bytes:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._session.get(NEU_REPO_ZIP_URL, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError(f"NEU download failed: {exc}") from exc

            if response.status_code != 200:
                if response.status_code in (502, 503, 504) and attempt + 1 < self.max_retries:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError(f"NEU download HTTP {response.status_code}")

            return response.content

        raise RuntimeError(f"NEU download failed after retries: {last_error}")

    def _extract_items(self, payload: bytes, items_dir: Path) -> int:
        count = 0
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            prefix = self._items_prefix(archive)
            for name in archive.namelist():
                if not name.startswith(prefix) or not name.endswith(".json"):
                    continue
                filename = name[len(prefix) :]
                if not filename or "/" in filename:
                    continue
                target = items_dir / filename
                target.write_bytes(archive.read(name))
                count += 1
        return count

    @staticmethod
    def _items_prefix(archive: zipfile.ZipFile) -> str:
        for name in archive.namelist():
            if "/items/" in name and name.endswith(".json"):
                return name.rsplit("/", 1)[0] + "/"
        raise RuntimeError("NEU zip archive does not contain items/*.json")

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> NeuItemsImporter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def parse_neu_item_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    item_id = str(data.get("internalname") or "").strip()
    if not item_id:
        return None

    lore = data.get("lore")
    lore_lines: list[str] | None = None
    if isinstance(lore, list):
        lore_lines = [str(line) for line in lore]

    display_name = str(data.get("displayname") or "")
    return {
        "item_id": item_id,
        "display_name": display_name,
        "lore": lore_lines,
        "source": "neu",
    }


def load_neu_tooltips(items_dir: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not items_dir.is_dir():
        return records

    for path in items_dir.glob("*.json"):
        parsed = parse_neu_item_file(path)
        if parsed is None:
            continue
        lore = parsed.get("lore") or []
        display_name = str(parsed.get("display_name") or "")
        title = display_name.replace("§", "&") if display_name else ""
        text = "/".join(str(line).replace("§", "&") for line in lore)
        records[parsed["item_id"]] = {
            "item_id": parsed["item_id"],
            "title": title or f"&f{parsed['item_id']}",
            "text": text,
            "lore": parsed.get("lore"),
            "source": "neu",
        }
    return records
