"""SkyBlock inventory containers parsed from Hypixel profile NBT."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ContainerStatus = Literal["ok", "empty", "hidden", "error"]
ContainerLayout = Literal["grid", "armor_equipment", "armor_column", "player_inventory"]


@dataclass(frozen=True)
class ItemStack:
    slot: int
    item_id: str | None
    name: str | None
    display_name: str | None
    lore: list[str] = field(default_factory=list)
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "item_id": self.item_id,
            "name": self.name,
            "display_name": self.display_name,
            "lore": self.lore,
            "count": self.count,
        }


@dataclass(frozen=True)
class InventoryPage:
    index: int
    label: str
    slot_count: int
    slot_offset: int = 0
    items: list[ItemStack] = field(default_factory=list)

    @property
    def filled_slots(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "label": self.label,
            "slot_count": self.slot_count,
            "slot_offset": self.slot_offset,
            "filled_slots": self.filled_slots,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class InventoryContainer:
    id: str
    label: str
    slot_count: int
    status: ContainerStatus
    items: list[ItemStack] = field(default_factory=list)
    message: str | None = None
    pages: list[InventoryPage] = field(default_factory=list)
    layout: ContainerLayout = "grid"
    equipped_set_index: int | None = None

    @property
    def filled_slots(self) -> int:
        if self.pages:
            return sum(page.filled_slots for page in self.pages)
        return len(self.items)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "slot_count": self.slot_count,
            "status": self.status,
            "filled_slots": self.filled_slots,
            "message": self.message,
            "layout": self.layout,
            "items": [item.to_dict() for item in self.items],
        }
        if self.pages:
            payload["pages"] = [page.to_dict() for page in self.pages]
            payload["page_count"] = self.page_count
        if self.equipped_set_index is not None:
            payload["equipped_set_index"] = self.equipped_set_index
        return payload


@dataclass(frozen=True)
class InventoriesSummary:
    containers: list[InventoryContainer] = field(default_factory=list)

    @property
    def any_available(self) -> bool:
        return any(c.status in ("ok", "empty") for c in self.containers)

    @property
    def inventory_api_enabled(self) -> bool:
        return any(c.status != "hidden" for c in self.containers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.any_available,
            "inventory_api_enabled": self.inventory_api_enabled,
            "containers": [container.to_dict() for container in self.containers],
        }


@dataclass(frozen=True)
class CollectionEntry:
    item_id: str
    display_name: str
    amount: int
    collection_type: str = "other"

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "display_name": self.display_name,
            "amount": self.amount,
            "collection_type": self.collection_type,
        }


@dataclass(frozen=True)
class CollectionGroup:
    id: str
    label: str
    entry_count: int
    total_amount: int
    entries: list[CollectionEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "entry_count": self.entry_count,
            "total_amount": self.total_amount,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class CollectionsSummary:
    entries: list[CollectionEntry] = field(default_factory=list)
    total_items: int = 0
    groups: list[CollectionGroup] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return bool(self.entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "total_items": self.total_items,
            "entry_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
            "groups": [group.to_dict() for group in self.groups],
        }
