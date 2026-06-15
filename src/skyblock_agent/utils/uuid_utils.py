"""UUID formatting helpers."""

from __future__ import annotations


def normalize_uuid(uuid: str) -> str:
    """Return lowercase UUID without dashes (Hypixel API format)."""
    return uuid.replace("-", "").lower()


def format_uuid_dashed(uuid: str) -> str:
    """Return lowercase UUID with dashes."""
    raw = normalize_uuid(uuid)
    if len(raw) != 32:
        return uuid.lower()
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"
