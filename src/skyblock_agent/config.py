"""Project paths and environment configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(
    os.getenv("SKYBLOCK_AGENT_DATA_DIR", PROJECT_ROOT / "data")
).resolve()
RAW_HYPIXEL_DIR = DATA_DIR / "raw" / "hypixel_api"

HYPIXEL_API_BASE = "https://api.hypixel.net"
MOJANG_PROFILE_LOOKUP = (
    "https://api.minecraftservices.com/minecraft/profile/lookup/name"
)
MOJANG_LEGACY_PROFILE_LOOKUP = "https://api.mojang.com/users/profiles/minecraft"
MOJANG_ASHCON_LOOKUP = "https://api.ashcon.app/mojang/v2/user"
MOJANG_LEGACY_PROFILE_LOOKUP = "https://api.mojang.com/users/profiles/minecraft"
ASHCON_PROFILE_LOOKUP = "https://api.ashcon.app/mojang/v2/user"

_PLACEHOLDER_KEYS = frozenset(
    {
        "",
        "your-api-key-here",
        "your-hypixel-api-key",
        "changeme",
    }
)


def get_api_key() -> str:
    key = os.getenv("HYPIXEL_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "HYPIXEL_API_KEY is not set. Copy .env.example to .env and add your key "
            "(get one in-game with /api new)."
        )
    if key.lower() in _PLACEHOLDER_KEYS:
        raise RuntimeError(
            "HYPIXEL_API_KEY is still the placeholder value. Edit .env and paste the key "
            "from /api new on Hypixel."
        )
    return key


def is_api_key_configured() -> bool:
    key = os.getenv("HYPIXEL_API_KEY", "").strip()
    return bool(key) and key.lower() not in _PLACEHOLDER_KEYS
