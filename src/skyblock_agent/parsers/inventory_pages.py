"""Split multi-page SkyBlock storage containers."""

from __future__ import annotations

import re

from typing import Any

from skyblock_agent.models.inventory import InventoryPage, ItemStack
from skyblock_agent.parsers.nbt_inventory import extract_encoded_data

# Ender chest upgrade tiers (total unlocked slots).
EC_CAPACITY_TIERS: tuple[int, ...] = (54, 99, 144, 189, 234, 279, 324, 369, 405)
EC_PAGE_SIZE = 45

# Backpack tiers in-game (Small → Jumbo).
BACKPACK_SIZES: tuple[int, ...] = (9, 18, 27, 36, 45)

# Accessory Bag redstone + account upgrade tiers (API field: talisman_bag).
ACCESSORY_BAG_TIERS: tuple[int, ...] = (3, 9, 15, 21, 27, 33, 39, 45, 51, 57)
ACCESSORY_BAG_PAGE_SIZE = 45
ACCESSORY_BAG_MAX_SLOTS = 255

# Wardrobe armor pieces per saved set (in-game /wd UI layout).
WARDROBE_SET_SLOTS = 4
WARDROBE_SETS_PER_PAGE = 9
WARDROBE_PAGE_SLOT_SPAN = 36
WARDROBE_MAX_SETS = 18

_WARDROBE_KEY = re.compile(r"^wd[\W_]*(\d+)$", re.IGNORECASE)


def classify_storage_key(key: str) -> str:
    """Classify keys inside ``backpack_contents`` (numeric = backpack, wd* = wardrobe)."""
    text = str(key).strip()
    if text.isdigit():
        return "backpack"
    if _WARDROBE_KEY.match(text) or text.lower().startswith("wardrobe"):
        return "wardrobe"
    return "unknown"


def parse_storage_key_index(key: str, *, fallback: int) -> int:
    text = str(key).strip()
    if text == "__all__":
        return 0
    if text.isdigit():
        return int(text)
    match = _WARDROBE_KEY.match(text)
    if match:
        return int(match.group(1))
    if text.lower().startswith("wardrobe"):
        digits = re.sub(r"\D", "", text)
        if digits:
            return int(digits)
    digits = re.sub(r"\D", "", text)
    if digits:
        return int(digits)
    return fallback


def is_inventory_blob(raw: Any) -> bool:
    """True when ``raw`` is a single Hypixel inventory payload (``{data, type?}`` or str)."""
    if isinstance(raw, str):
        return bool(raw.strip())
    if not isinstance(raw, dict):
        return False
    if extract_encoded_data(raw) is None:
        return False
    meta_keys = {str(key).lower() for key in raw.keys()}
    return meta_keys <= {"data", "type"}


def _copy_stack_to_local(stack: ItemStack, local_slot: int) -> ItemStack:
    return ItemStack(
        slot=local_slot,
        item_id=stack.item_id,
        name=stack.name,
        display_name=stack.display_name,
        lore=stack.lore,
        count=stack.count,
    )


def _wardrobe_item_stacks(stacks: list[ItemStack]) -> list[ItemStack]:
    return [stack for stack in stacks if stack.item_id]


def _wardrobe_uses_column_layout(stacks: list[ItemStack]) -> bool:
    """Detect column (0/9/18/27) vs linear (0-3, 4-7, …) wardrobe storage."""
    items = _wardrobe_item_stacks(stacks)
    slots = {stack.slot for stack in items}
    if not slots:
        return False

    for idx in range(WARDROBE_SETS_PER_PAGE):
        if sum(1 for offset in (0, 9, 18, 27) if idx + offset in slots) >= 3:
            return True

    for set_index in range(WARDROBE_MAX_SETS):
        base = set_index * WARDROBE_SET_SLOTS
        if base not in slots:
            continue
        if all(base + piece in slots for piece in range(1, 4)):
            return False
        if all(base + piece in slots for piece in range(4)):
            return False

    return bool(slots & {9, 18, 27})


def extract_wardrobe_set_items(
    stacks: list[ItemStack],
    set_index: int,
    *,
    column_layout: bool | None = None,
) -> list[ItemStack]:
    """Extract one wardrobe set using column or linear slot layout."""
    items = _wardrobe_item_stacks(stacks)
    if set_index < 0 or set_index >= WARDROBE_MAX_SETS:
        return []

    if column_layout is None:
        column_layout = _wardrobe_uses_column_layout(items)

    if column_layout:
        by_slot = {stack.slot: stack for stack in items}
        page = set_index // WARDROBE_SETS_PER_PAGE
        idx = set_index % WARDROBE_SETS_PER_PAGE
        base = page * WARDROBE_PAGE_SLOT_SPAN

        items: list[ItemStack] = []
        for local, column_offset in enumerate((0, 9, 18, 27)):
            stack = by_slot.get(base + column_offset + idx)
            if stack is not None:
                items.append(_copy_stack_to_local(stack, local))
        return items

    linear_offset = set_index * WARDROBE_SET_SLOTS
    return _remap_page_items(items, linear_offset, WARDROBE_SET_SLOTS)


def build_wardrobe_pages_from_blob(stacks: list[ItemStack]) -> list[InventoryPage]:
    items = _wardrobe_item_stacks(stacks)
    column_layout = _wardrobe_uses_column_layout(items)
    pages: list[InventoryPage] = []
    for set_index in range(WARDROBE_MAX_SETS):
        page_items = extract_wardrobe_set_items(items, set_index, column_layout=column_layout)
        if not page_items or not any(item.item_id for item in page_items):
            continue
        pages.append(
            InventoryPage(
                index=set_index,
                label=f"Set {set_index + 1}",
                slot_count=WARDROBE_SET_SLOTS,
                slot_offset=0,
                items=page_items,
            )
        )
    return pages


def build_wardrobe_page(*, index: int, stacks: list[ItemStack]) -> InventoryPage:
    page_items = extract_wardrobe_set_items(_wardrobe_item_stacks(stacks), 0)
    return InventoryPage(
        index=index,
        label=f"Set {index + 1}",
        slot_count=WARDROBE_SET_SLOTS,
        slot_offset=0,
        items=page_items,
    )


def infer_tiered_capacity(max_slot: int, tiers: tuple[int, ...], *, default: int) -> int:
    if max_slot < 0:
        return default
    needed = max_slot + 1
    for capacity in tiers:
        if capacity >= needed:
            return capacity
    return tiers[-1]


def infer_backpack_size(max_slot: int) -> int:
    return infer_tiered_capacity(max_slot, BACKPACK_SIZES, default=BACKPACK_SIZES[0])


def infer_ender_chest_capacity(max_slot: int) -> int:
    return infer_tiered_capacity(max_slot, EC_CAPACITY_TIERS, default=EC_CAPACITY_TIERS[0])


def infer_accessory_bag_capacity(max_slot: int) -> int:
    if max_slot < 0:
        return ACCESSORY_BAG_TIERS[0]
    needed = max_slot + 1
    for capacity in ACCESSORY_BAG_TIERS:
        if capacity >= needed:
            return capacity
    page_slots = ((needed + ACCESSORY_BAG_PAGE_SIZE - 1) // ACCESSORY_BAG_PAGE_SIZE) * ACCESSORY_BAG_PAGE_SIZE
    return min(ACCESSORY_BAG_MAX_SLOTS, max(page_slots, ACCESSORY_BAG_TIERS[-1]))


def split_fixed_pages(total_slots: int, *, page_size: int = EC_PAGE_SIZE) -> list[tuple[int, int]]:
    """Return ``(slot_offset, page_slot_count)`` pairs for each page."""
    if total_slots <= 0:
        return []
    pages: list[tuple[int, int]] = []
    offset = 0
    while offset < total_slots:
        count = min(page_size, total_slots - offset)
        pages.append((offset, count))
        offset += page_size
    return pages


def _remap_page_items(stacks: list[ItemStack], offset: int, count: int) -> list[ItemStack]:
    by_slot = {stack.slot: stack for stack in stacks}
    page_items: list[ItemStack] = []
    for local in range(count):
        global_slot = offset + local
        stack = by_slot.get(global_slot)
        if stack is None:
            continue
        page_items.append(
            ItemStack(
                slot=local,
                item_id=stack.item_id,
                name=stack.name,
                display_name=stack.display_name,
                lore=stack.lore,
                count=stack.count,
            )
        )
    return page_items


def build_ender_chest_pages(stacks: list[ItemStack]) -> list[InventoryPage]:
    max_slot = max((stack.slot for stack in stacks), default=-1)
    total_slots = infer_ender_chest_capacity(max_slot)
    pages: list[InventoryPage] = []
    for index, (offset, count) in enumerate(split_fixed_pages(total_slots)):
        page_items = _remap_page_items(stacks, offset, count)
        pages.append(
            InventoryPage(
                index=index,
                label=f"Page {index + 1}",
                slot_count=count,
                slot_offset=offset,
                items=page_items,
            )
        )
    return pages


def build_accessory_bag_pages(stacks: list[ItemStack]) -> list[InventoryPage]:
    max_slot = max((stack.slot for stack in stacks), default=-1)
    total_slots = infer_accessory_bag_capacity(max_slot)
    pages: list[InventoryPage] = []
    for index, (offset, count) in enumerate(
        split_fixed_pages(total_slots, page_size=ACCESSORY_BAG_PAGE_SIZE)
    ):
        page_items = _remap_page_items(stacks, offset, count)
        pages.append(
            InventoryPage(
                index=index,
                label=f"Page {index + 1}",
                slot_count=count,
                slot_offset=offset,
                items=page_items,
            )
        )
    return pages


def build_backpack_page(*, index: int, stacks: list[ItemStack]) -> InventoryPage:
    max_slot = max((stack.slot for stack in stacks), default=-1)
    slot_count = infer_backpack_size(max_slot)
    page_items = _remap_page_items(stacks, 0, slot_count)
    return InventoryPage(
        index=index,
        label=f"Backpack {index + 1}",
        slot_count=slot_count,
        slot_offset=0,
        items=page_items,
    )

