"""Fetch raw Lua module sources from the Hypixel SkyBlock Wiki (Fandom)."""

from __future__ import annotations

import time
from typing import Any

import requests

WIKI_API_BASE = "https://hypixel-skyblock.fandom.com/api.php"


class WikiClient:
    """MediaWiki API client for SkyBlock wiki module pages."""

    def __init__(self, *, timeout: float = 120.0, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "skyblock-agent/0.1.0 (tooltip sync; +https://github.com/Winneriswin/skyblock-agent)",
            }
        )

    def get_module_source(self, title: str) -> str:
        """Return wikitext/lua source for a ``Module:...`` page."""
        params = {
            "action": "query",
            "titles": title,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "format": "json",
            "formatversion": "2",
        }
        payload = self._request(params)
        pages = payload.get("query", {}).get("pages") or []
        if not pages:
            raise RuntimeError(f"Wiki page not found: {title}")
        page = pages[0]
        if page.get("missing"):
            raise RuntimeError(f"Wiki page not found: {title}")
        revisions = page.get("revisions") or []
        if not revisions:
            raise RuntimeError(f"Wiki page has no revisions: {title}")
        slots = revisions[0].get("slots") or {}
        content = slots.get("main", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"Wiki page has empty content: {title}")
        return content

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._session.get(WIKI_API_BASE, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise RuntimeError(f"Wiki request failed: {exc}") from exc

            if response.status_code == 429:
                if attempt + 1 < self.max_retries:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError("Wiki rate limited (HTTP 429)")

            if response.status_code != 200:
                raise RuntimeError(
                    f"Wiki API error {response.status_code}: {response.text[:200]}"
                )

            return response.json()

        raise RuntimeError(f"Wiki request failed after retries: {last_error}")

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> WikiClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
