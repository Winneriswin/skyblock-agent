"""Mojang username to UUID lookup with retries and fallback providers."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

import requests

from skyblock_agent.config import (
    MOJANG_ASHCON_LOOKUP,
    MOJANG_LEGACY_PROFILE_LOOKUP,
    MOJANG_PROFILE_LOOKUP,
)
from skyblock_agent.collectors.hypixel_client import HypixelApiError
from skyblock_agent.utils.uuid_utils import normalize_uuid

LookupFn = Callable[[requests.Session, str, float], Optional[str]]


class MojangClient:
    def __init__(self, *, timeout: float = 10.0, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update(
            {"Accept": "application/json", "User-Agent": "skyblock-agent/0.1.0"}
        )
        self._providers: tuple[tuple[str, LookupFn], ...] = (
            ("minecraftservices", _lookup_minecraftservices),
            ("mojang", _lookup_mojang_legacy),
            ("ashcon", _lookup_ashcon),
        )

    def lookup_uuid(self, username: str) -> str | None:
        name = username.strip()
        if not name:
            return None

        errors: list[str] = []
        for provider_name, provider in self._providers:
            for attempt in range(self.max_retries):
                try:
                    uuid = provider(self._session, name, self.timeout)
                except requests.RequestException as exc:
                    detail = f"{provider_name} attempt {attempt + 1}: {exc}"
                    errors.append(detail)
                    if attempt + 1 < self.max_retries:
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    break

                if uuid:
                    return uuid
                return None

        if errors:
            raise HypixelApiError(
                "Mojang lookup failed after retries and fallbacks. "
                + "; ".join(errors[-3:])
            )
        return None

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> MojangClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _lookup_minecraftservices(
    session: requests.Session, username: str, timeout: float
) -> str | None:
    url = f"{MOJANG_PROFILE_LOOKUP}/{username.lower()}"
    response = session.get(url, timeout=timeout)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise requests.HTTPError(
            f"minecraftservices {response.status_code}: {response.text[:200]}",
            response=response,
        )
    return _uuid_from_payload(response.json(), ("id",))


def _lookup_mojang_legacy(
    session: requests.Session, username: str, timeout: float
) -> str | None:
    url = f"{MOJANG_LEGACY_PROFILE_LOOKUP}/{username}"
    response = session.get(url, timeout=timeout)
    if response.status_code == 404:
        return None
    if response.status_code == 204:
        return None
    if response.status_code != 200:
        raise requests.HTTPError(
            f"mojang legacy {response.status_code}: {response.text[:200]}",
            response=response,
        )
    return _uuid_from_payload(response.json(), ("id",))


def _lookup_ashcon(
    session: requests.Session, username: str, timeout: float
) -> str | None:
    url = f"{MOJANG_ASHCON_LOOKUP}/{username}"
    response = session.get(url, timeout=timeout)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise requests.HTTPError(
            f"ashcon {response.status_code}: {response.text[:200]}",
            response=response,
        )
    return _uuid_from_payload(response.json(), ("uuid", "id"))


def _uuid_from_payload(payload: Any, keys: tuple[str, ...]) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_uuid(value)
    return None
