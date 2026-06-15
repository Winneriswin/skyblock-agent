"""Low-level Hypixel Public API HTTP client."""

from __future__ import annotations

import time
from typing import Any

import requests

from skyblock_agent.config import HYPIXEL_API_BASE, get_api_key


class HypixelApiError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class HypixelClient:
    """Thin wrapper around Hypixel v2 endpoints (pattern from Skyblocker ProfileUtils)."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 15.0,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or get_api_key()
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update(
            {
                "API-Key": self.api_key,
                "Accept": "application/json",
                "User-Agent": "skyblock-agent/0.1.0",
            }
        )

    def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{HYPIXEL_API_BASE}/{path.lstrip('/')}"
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self._session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise HypixelApiError(f"Request failed: {exc}") from exc

            if response.status_code == 429:
                if attempt + 1 < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise HypixelApiError("Rate limited by Hypixel API", status_code=429)

            if response.status_code != 200:
                raise HypixelApiError(
                    f"Hypixel API error {response.status_code}: {response.text[:200]}",
                    status_code=response.status_code,
                )

            payload = response.json()
            if not payload.get("success", False):
                cause = payload.get("cause", "unknown")
                raise HypixelApiError(f"Hypixel API returned success=false: {cause}")

            return payload

        raise HypixelApiError(f"Request failed after retries: {last_error}")

    def get_player(self, uuid: str) -> dict[str, Any]:
        return self.get("v2/player", {"uuid": uuid})

    def get_skyblock_profiles(self, uuid: str) -> dict[str, Any]:
        return self.get("v2/skyblock/profiles", {"uuid": uuid})

    def get_skyblock_profile(self, profile_id: str) -> dict[str, Any]:
        return self.get("v2/skyblock/profile", {"profile": profile_id})

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> HypixelClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
