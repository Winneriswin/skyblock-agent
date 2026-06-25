"""Catacombs / dungeon stats parsed from Hypixel profile member data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DungeonMode = Literal["normal", "master"]

DUNGEON_CLASS_ORDER: tuple[str, ...] = ("healer", "mage", "berserk", "archer", "tank")

DUNGEON_CLASS_LABELS: dict[str, str] = {
    "healer": "Healer",
    "mage": "Mage",
    "berserk": "Berserk",
    "archer": "Archer",
    "tank": "Tank",
}


@dataclass(frozen=True)
class DungeonClassInfo:
    id: str
    label: str
    experience: float
    level: float
    selected: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "experience": self.experience,
            "level": self.level,
            "selected": self.selected,
        }


@dataclass(frozen=True)
class DungeonFloorStats:
    floor: int
    label: str
    completions: int
    pb_s_ms: float | None
    pb_s_plus_ms: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "floor": self.floor,
            "label": self.label,
            "completions": self.completions,
            "pb_s_ms": self.pb_s_ms,
            "pb_s_plus_ms": self.pb_s_plus_ms,
        }


@dataclass(frozen=True)
class DungeonModeStats:
    mode: DungeonMode
    label: str
    floors: list[DungeonFloorStats] = field(default_factory=list)

    @property
    def total_completions(self) -> int:
        return sum(floor.completions for floor in self.floors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "label": self.label,
            "total_completions": self.total_completions,
            "floors": [floor.to_dict() for floor in self.floors],
        }


@dataclass(frozen=True)
class CatacombsSummary:
    available: bool
    experience: float | None = None
    level: float | None = None
    selected_class: str | None = None
    selected_class_label: str | None = None
    classes: list[DungeonClassInfo] = field(default_factory=list)
    modes: list[DungeonModeStats] = field(default_factory=list)
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "experience": self.experience,
            "level": self.level,
            "selected_class": self.selected_class,
            "selected_class_label": self.selected_class_label,
            "classes": [entry.to_dict() for entry in self.classes],
            "modes": [mode.to_dict() for mode in self.modes],
            "message": self.message,
        }
