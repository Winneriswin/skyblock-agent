"""Mojang username to UUID lookup (same endpoint used by NEU ProfileViewer)."""

from __future__ import annotations

import requests

from skyblock_agent.config import MOJANG_PROFILE_LOOKUP
from skyblock_agent.collectors.hypixel_client import HypixelApiError
from skyblock_agent.utils.uuid_utils import normalize_uuid


class MojangClient:
    def __init__(self, *, timeout: float = 10.0) -> None:
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {"Accept": "application/json", "User-Agent": "skyblock-agent/0.1.0"}
        )

    def lookup_uuid(self, username: str) -> str | None:
        name = username.strip()
        if not name:
            return None

        url = f"{MOJANG_PROFILE_LOOKUP}/{name.lower()}"
        try:
            response = self._session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise HypixelApiError(f"Mojang lookup failed: {exc}") from exc

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise HypixelApiError(
                f"Mojang lookup error {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        data = response.json()
        player_id = data.get("id")
        if not isinstance(player_id, str):
            return None
        return normalize_uuid(player_id)

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> MojangClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
