"""Local index of imported players (username -> API snapshot metadata)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skyblock_agent.config import DATA_DIR

INDEX_PATH = DATA_DIR / "processed" / "players" / "index.json"


@dataclass
class PlayerImportRecord:
    username: str
    uuid: str
    last_imported_at: str
    profiles: list[str] = field(default_factory=list)
    selected_profile: str | None = None
    saved_files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        return {"players": {}}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _save_index(index: dict[str, Any]) -> Path:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return INDEX_PATH


def upsert_player(record: PlayerImportRecord) -> Path:
    index = _load_index()
    players = index.setdefault("players", {})
    players[record.username.lower()] = record.to_dict()
    return _save_index(index)


def get_player(username: str) -> PlayerImportRecord | None:
    entry = _load_index().get("players", {}).get(username.lower())
    if not isinstance(entry, dict):
        return None
    return PlayerImportRecord(
        username=str(entry.get("username", username)),
        uuid=str(entry.get("uuid", "")),
        last_imported_at=str(entry.get("last_imported_at", "")),
        profiles=list(entry.get("profiles") or []),
        selected_profile=entry.get("selected_profile"),
        saved_files=dict(entry.get("saved_files") or {}),
    )


def delete_player(username: str, *, delete_files: bool = True) -> bool:
    index = _load_index()
    players = index.setdefault("players", {})
    key = username.strip().lower()
    entry = players.get(key)
    if not isinstance(entry, dict):
        return False

    if delete_files:
        for path_str in (entry.get("saved_files") or {}).values():
            try:
                path = Path(str(path_str))
                if path.is_file():
                    path.unlink()
            except OSError:
                pass

    del players[key]
    _save_index(index)
    return True


def list_players() -> list[PlayerImportRecord]:
    players = _load_index().get("players", {})
    records: list[PlayerImportRecord] = []
    for entry in players.values():
        if not isinstance(entry, dict):
            continue
        records.append(
            PlayerImportRecord(
                username=str(entry.get("username", "")),
                uuid=str(entry.get("uuid", "")),
                last_imported_at=str(entry.get("last_imported_at", "")),
                profiles=list(entry.get("profiles") or []),
                selected_profile=entry.get("selected_profile"),
                saved_files=dict(entry.get("saved_files") or {}),
            )
        )
    records.sort(key=lambda item: item.last_imported_at, reverse=True)
    return records


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
