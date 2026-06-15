"""Persist raw API responses for migration and offline use."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skyblock_agent.config import RAW_HYPIXEL_DIR
from skyblock_agent.utils.uuid_utils import normalize_uuid


def save_raw_json(category: str, key: str, payload: dict[str, Any]) -> Path:
    directory = RAW_HYPIXEL_DIR / category
    directory.mkdir(parents=True, exist_ok=True)

    safe_key = normalize_uuid(key) if len(key.replace("-", "")) == 32 else key
    path = directory / f"{safe_key}.json"
    envelope = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
