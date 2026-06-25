"""Download SkyBlock item icons from public sources into local PNG files."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MIN_ICON_BYTES = 64

COFLNET_ICON_BASE = "https://sky.coflnet.com/static/icon"
MINECRAFT_ASSETS_BASE = (
    "https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/1.21.4"
)


class IconSource(str, Enum):
    COFLNET = "coflnet"
    VANILLA_ITEM = "vanilla_item"
    VANILLA_BLOCK = "vanilla_block"


@dataclass(frozen=True)
class IconFetchResult:
    item_id: str
    data: bytes
    source: IconSource
    source_url: str


class IconClient:
    """Resolve item icons: Coflnet (SkyBlock) first, then vanilla Minecraft textures."""

    def __init__(self, *, timeout: float = 30.0, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "image/png,image/*",
                "User-Agent": "skyblock-agent/0.1.0",
            }
        )

    def fetch_vanilla_icon(self, material: str) -> IconFetchResult | None:
        """Fetch Minecraft vanilla item/block texture for a SkyBlock ``material`` id."""
        return self._fetch_vanilla(material)

    def fetch_icon(
        self,
        item_id: str,
        *,
        material: str | None = None,
    ) -> IconFetchResult | None:
        item_id = item_id.strip().upper()
        if not item_id:
            return None

        coflnet = self._fetch_coflnet(item_id)
        if coflnet is not None:
            return coflnet

        if material:
            vanilla = self._fetch_vanilla(material)
            if vanilla is not None:
                return IconFetchResult(
                    item_id=item_id,
                    data=vanilla.data,
                    source=vanilla.source,
                    source_url=vanilla.source_url,
                )

        return None

    def _fetch_coflnet(self, item_id: str) -> IconFetchResult | None:
        url = f"{COFLNET_ICON_BASE}/{item_id}"
        data = self._get_bytes(url)
        if data is None:
            return None
        return IconFetchResult(
            item_id=item_id,
            data=data,
            source=IconSource.COFLNET,
            source_url=url,
        )

    def _fetch_vanilla(self, material: str) -> IconFetchResult | None:
        slug = _material_slug(material)
        if not slug:
            return None

        for folder, source in (
            ("items", IconSource.VANILLA_ITEM),
            ("blocks", IconSource.VANILLA_BLOCK),
        ):
            url = f"{MINECRAFT_ASSETS_BASE}/{folder}/{slug}.png"
            data = self._get_bytes(url)
            if data is not None:
                return IconFetchResult(
                    item_id=material.upper(),
                    data=data,
                    source=source,
                    source_url=url,
                )
        return None

    def _get_bytes(self, url: str) -> bytes | None:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._session.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return None

            if response.status_code == 429:
                if attempt + 1 < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return None

            if response.status_code != 200:
                return None

            content_type = (response.headers.get("Content-Type") or "").lower()
            data = response.content
            if not _looks_like_png(data, content_type):
                return None
            return data

        return None

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> IconClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _material_slug(material: str) -> str:
    slug = material.strip().lower()
    if slug.startswith("minecraft:"):
        slug = slug.split(":", 1)[1]
    return slug.replace(" ", "_")


def _looks_like_png(data: bytes, content_type: str) -> bool:
    if len(data) < MIN_ICON_BYTES:
        return False
    if not data.startswith(PNG_MAGIC):
        return False
    if content_type and "image" not in content_type and "octet-stream" not in content_type:
        return False
    return True
