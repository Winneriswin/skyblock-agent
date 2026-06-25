"""Extract inventory containers from a SkyBlock profile member payload."""

from __future__ import annotations

from typing import Any

from skyblock_agent.models.inventory import InventoriesSummary, InventoryContainer, InventoryPage, ItemStack
from skyblock_agent.parsers.inventory_pages import (
    build_accessory_bag_pages,
    build_backpack_page,
    build_ender_chest_pages,
    build_wardrobe_page,
    build_wardrobe_pages_from_blob,
    classify_storage_key,
    is_inventory_blob,
    parse_storage_key_index,
)
from skyblock_agent.parsers.nbt_inventory import extract_encoded_data, parse_inventory_blob, strip_color_codes
from skyblock_agent.storage.item_index import get_catalog_item

# Official in-game names (API field names differ where noted).
CONTAINER_ORDER: tuple[str, ...] = (
    "inventory",
    "armor_equipment",
    "accessory_bag",
    "ender_chest",
    "backpack",
    "wardrobe",
)

# Minecraft armor slot order in NBT: 0=boots, 1=legs, 2=chest, 3=helmet → display top-down.
ARMOR_DISPLAY_SLOTS: tuple[int, ...] = (3, 2, 1, 0)


ACCESSORY_BAG_TIER_DEFAULT = 3


def parse_member_inventories(member: dict[str, Any]) -> InventoriesSummary:
    inventory_root = member.get("inventory")
    if not isinstance(inventory_root, dict):
        return InventoriesSummary(containers=[_hidden_container(spec_id) for spec_id in CONTAINER_ORDER])

    parsed: dict[str, InventoryContainer] = {
        "inventory": _parse_inventory(inventory_root.get("inv_contents")),
        "armor_equipment": _parse_armor_and_equipment(
            inventory_root.get("inv_armor"),
            inventory_root.get("equipment_contents"),
        ),
        "accessory_bag": _parse_accessory_bag(inventory_root),
        "ender_chest": _parse_ender_chest(inventory_root.get("ender_chest_contents")),
        "backpack": _parse_backpack_storage(inventory_root.get("backpack_contents")),
        "wardrobe": _parse_wardrobe(member, inventory_root),
    }
    return InventoriesSummary(containers=[parsed[spec_id] for spec_id in CONTAINER_ORDER])


def _hidden_container(spec_id: str) -> InventoryContainer:
    defaults = {
        "inventory": ("Inventory", 36, "player_inventory"),
        "armor_equipment": ("Armor & Equipment", 8, "armor_equipment"),
        "accessory_bag": ("Accessory Bag", 3, "grid"),
        "ender_chest": ("Ender Chest", 54, "grid"),
        "backpack": ("Backpack", 0, "grid"),
        "wardrobe": ("Wardrobe", 0, "grid"),
    }
    label, slots, layout = defaults[spec_id]
    return InventoryContainer(
        id=spec_id,
        label=label,
        slot_count=slots,
        status="hidden",
        layout=layout,  # type: ignore[arg-type]
        message="Inventory API disabled in-game or no data returned.",
    )


def _parse_inventory(raw: Any) -> InventoryContainer:
    return _parse_simple_blob(
        spec_id="inventory",
        label="Inventory",
        slot_count=36,
        raw=raw,
        empty_message="Inventory is empty.",
        layout="player_inventory",
    )


def _parse_simple_blob(
    *,
    spec_id: str,
    label: str,
    slot_count: int,
    raw: Any,
    empty_message: str,
    layout: str = "grid",
) -> InventoryContainer:
    encoded = extract_encoded_data(raw)
    if encoded is None:
        return InventoryContainer(
            id=spec_id,
            label=label,
            slot_count=slot_count,
            status="hidden",
            layout=layout,  # type: ignore[arg-type]
            message="Not included in API response (check Inventory API setting).",
        )

    try:
        stacks = [_enrich_stack(stack) for stack in parse_inventory_blob(encoded)]
    except (ValueError, RuntimeError) as exc:
        return InventoryContainer(
            id=spec_id,
            label=label,
            slot_count=slot_count,
            status="error",
            layout=layout,  # type: ignore[arg-type]
            message=str(exc),
        )

    status = "ok" if stacks else "empty"
    message = None if stacks else empty_message
    return InventoryContainer(
        id=spec_id,
        label=label,
        slot_count=slot_count,
        status=status,
        items=stacks,
        layout=layout,  # type: ignore[arg-type]
        message=message,
    )


def _parse_armor_and_equipment(armor_raw: Any, equipment_raw: Any) -> InventoryContainer:
    armor_encoded = extract_encoded_data(armor_raw)
    equipment_encoded = extract_encoded_data(equipment_raw)
    if armor_encoded is None and equipment_encoded is None:
        return InventoryContainer(
            id="armor_equipment",
            label="Armor & Equipment",
            slot_count=8,
            status="hidden",
            layout="armor_equipment",
            message="Not included in API response (check Inventory API setting).",
        )

    combined: list[ItemStack] = []
    errors: list[str] = []

    if armor_encoded is not None:
        try:
            armor_stacks = [_enrich_stack(stack) for stack in parse_inventory_blob(armor_encoded)]
            by_slot = {stack.slot: stack for stack in armor_stacks}
            for display_slot, source_slot in enumerate(ARMOR_DISPLAY_SLOTS):
                stack = by_slot.get(source_slot)
                if stack is None:
                    continue
                combined.append(
                    ItemStack(
                        slot=display_slot,
                        item_id=stack.item_id,
                        name=stack.name,
                        display_name=stack.display_name,
                        lore=stack.lore,
                        count=stack.count,
                    )
                )
        except (ValueError, RuntimeError) as exc:
            errors.append(str(exc))

    if equipment_encoded is not None:
        try:
            equipment_stacks = [_enrich_stack(stack) for stack in parse_inventory_blob(equipment_encoded)]
            for stack in equipment_stacks:
                combined.append(
                    ItemStack(
                        slot=stack.slot + 4,
                        item_id=stack.item_id,
                        name=stack.name,
                        display_name=stack.display_name,
                        lore=stack.lore,
                        count=stack.count,
                    )
                )
        except (ValueError, RuntimeError) as exc:
            errors.append(str(exc))

    if errors and not combined:
        return InventoryContainer(
            id="armor_equipment",
            label="Armor & Equipment",
            slot_count=8,
            status="error",
            layout="armor_equipment",
            message=errors[0],
        )

    status = "ok" if combined else "empty"
    message = None if combined else "No armor or equipment equipped."
    return InventoryContainer(
        id="armor_equipment",
        label="Armor & Equipment",
        slot_count=8,
        status=status,
        items=combined,
        layout="armor_equipment",
        message=message,
    )


def _get_accessory_bag_raw(inv: dict[str, Any]) -> Any:
    bag_contents = inv.get("bag_contents")
    if isinstance(bag_contents, dict):
        for key in ("talisman_bag", "TALISMAN_BAG"):
            if key in bag_contents:
                return bag_contents[key]
    return inv.get("talisman_bag")


def _parse_accessory_bag(inv: dict[str, Any]) -> InventoryContainer:
    raw = _get_accessory_bag_raw(inv)
    encoded = extract_encoded_data(raw)
    if encoded is None:
        return InventoryContainer(
            id="accessory_bag",
            label="Accessory Bag",
            slot_count=ACCESSORY_BAG_TIER_DEFAULT,
            status="hidden",
            message="Not included in API response (check Inventory API setting).",
        )

    try:
        stacks = [_enrich_stack(stack) for stack in parse_inventory_blob(encoded)]
    except (ValueError, RuntimeError) as exc:
        return InventoryContainer(
            id="accessory_bag",
            label="Accessory Bag",
            slot_count=3,
            status="error",
            message=str(exc),
        )

    pages = build_accessory_bag_pages(stacks)
    total_slots = sum(page.slot_count for page in pages)
    status = "ok" if stacks else "empty"
    message = None if stacks else "Accessory Bag is empty."
    return InventoryContainer(
        id="accessory_bag",
        label="Accessory Bag",
        slot_count=total_slots,
        status=status,
        items=stacks,
        pages=pages,
        message=message,
    )


def _parse_ender_chest(raw: Any) -> InventoryContainer:
    encoded = extract_encoded_data(raw)
    if encoded is None:
        return InventoryContainer(
            id="ender_chest",
            label="Ender Chest",
            slot_count=54,
            status="hidden",
            message="Not included in API response (check Inventory API setting).",
        )

    try:
        stacks = [_enrich_stack(stack) for stack in parse_inventory_blob(encoded)]
    except (ValueError, RuntimeError) as exc:
        return InventoryContainer(
            id="ender_chest",
            label="Ender Chest",
            slot_count=54,
            status="error",
            message=str(exc),
        )

    pages = build_ender_chest_pages(stacks)
    total_slots = sum(page.slot_count for page in pages)
    status = "ok" if stacks else "empty"
    message = None if stacks else "Ender Chest is empty."
    return InventoryContainer(
        id="ender_chest",
        label="Ender Chest",
        slot_count=total_slots,
        status=status,
        items=stacks,
        pages=pages,
        message=message,
    )


def _parse_backpack_storage(raw: Any) -> InventoryContainer:
    if raw is None:
        return InventoryContainer(
            id="backpack",
            label="Backpack",
            slot_count=0,
            status="hidden",
            message="Not included in API response (check Inventory API setting).",
        )

    entries = _iter_dict_entries(raw, kind="backpack")
    return _parse_paged_dict_storage(
        spec_id="backpack",
        label="Backpack",
        entries=entries,
        page_builder=build_backpack_page,
        empty_message="No backpacks in storage.",
    )


def _parse_wardrobe(member: dict[str, Any], inventory_root: dict[str, Any]) -> InventoryContainer:
    wardrobe_raw = inventory_root.get("wardrobe_contents")
    if wardrobe_raw is None:
        wardrobe_raw = member.get("wardrobe_contents")
    backpack_raw = inventory_root.get("backpack_contents")

    pages: list[InventoryPage] = []
    parse_errors: list[str] = []

    if is_inventory_blob(wardrobe_raw):
        pages.extend(_parse_wardrobe_blob(wardrobe_raw, parse_errors))
    elif isinstance(wardrobe_raw, dict):
        if extract_encoded_data(wardrobe_raw) is not None and all(
            str(key).lower() in {"data", "type"} for key in wardrobe_raw.keys()
        ):
            pages.extend(_parse_wardrobe_blob(wardrobe_raw, parse_errors))
        else:
            for key, entry in sorted(wardrobe_raw.items(), key=lambda item: parse_storage_key_index(item[0], fallback=0)):
                if str(key).lower() in {"data", "type"}:
                    continue
                pages.extend(_parse_wardrobe_entry(str(key), entry, parse_errors))

    for key, entry in _iter_dict_entries(backpack_raw, kind="wardrobe"):
        pages.extend(_parse_wardrobe_entry(key, entry, parse_errors))

    if not pages and wardrobe_raw is None and backpack_raw is None:
        return InventoryContainer(
            id="wardrobe",
            label="Wardrobe",
            slot_count=0,
            status="hidden",
            message="Not included in API response (check Inventory API setting).",
        )

    if not pages:
        equipped_slot = inventory_root.get("wardrobe_equipped_slot")
        has_equipped = isinstance(equipped_slot, int) and equipped_slot >= 0
        if parse_errors:
            return InventoryContainer(
                id="wardrobe",
                label="Wardrobe",
                slot_count=0,
                status="error",
                message=parse_errors[0],
            )
        if has_equipped:
            fallback = _build_equipped_wardrobe_fallback(inventory_root, equipped_slot)
            if fallback is not None:
                return fallback
            return InventoryContainer(
                id="wardrobe",
                label="Wardrobe",
                slot_count=4,
                status="empty",
                message=(
                    f"Hypixel returned equipped set #{equipped_slot + 1} but no wardrobe storage "
                    f"or equipped armor in the API response. Saved wardrobe sets are often omitted "
                    f"even when Inventory API is enabled."
                ),
            )
        return InventoryContainer(
            id="wardrobe",
            label="Wardrobe",
            slot_count=0,
            status="empty",
            message="Wardrobe is empty.",
        )

    pages.sort(key=lambda page: page.index)
    total_slots = sum(page.slot_count for page in pages)
    all_items = [item for page in pages for item in page.items]
    status = "ok" if all_items else "empty"
    message = None if all_items else "Wardrobe is empty."
    equipped_raw = inventory_root.get("wardrobe_equipped_slot")
    equipped_set_index: int | None = None
    if isinstance(equipped_raw, int) and equipped_raw >= 0:
        equipped_set_index = equipped_raw
    return InventoryContainer(
        id="wardrobe",
        label="Wardrobe",
        slot_count=total_slots,
        status=status,
        items=all_items,
        pages=pages,
        message=message,
        layout="armor_column",
        equipped_set_index=equipped_set_index,
    )


def _armor_items_from_inv_armor(armor_raw: Any) -> list[ItemStack]:
    encoded = extract_encoded_data(armor_raw)
    if encoded is None:
        return []
    try:
        armor_stacks = [_enrich_stack(stack) for stack in parse_inventory_blob(encoded)]
    except (ValueError, RuntimeError):
        return []

    by_slot = {stack.slot: stack for stack in armor_stacks if stack.item_id}
    items: list[ItemStack] = []
    for display_slot, source_slot in enumerate(ARMOR_DISPLAY_SLOTS):
        stack = by_slot.get(source_slot)
        if stack is None:
            continue
        items.append(
            ItemStack(
                slot=display_slot,
                item_id=stack.item_id,
                name=stack.name,
                display_name=stack.display_name,
                lore=stack.lore,
                count=stack.count,
            )
        )
    return items


def _build_equipped_wardrobe_fallback(
    inventory_root: dict[str, Any],
    equipped_slot: int,
) -> InventoryContainer | None:
    """Show currently worn armor when Hypixel omits ``wardrobe_contents``."""
    items = _armor_items_from_inv_armor(inventory_root.get("inv_armor"))
    if not items:
        return None

    page = InventoryPage(
        index=equipped_slot,
        label=f"Set {equipped_slot + 1} (equipped armor)",
        slot_count=4,
        items=items,
    )
    return InventoryContainer(
        id="wardrobe",
        label="Wardrobe",
        slot_count=4,
        status="ok",
        items=items,
        pages=[page],
        layout="armor_column",
        equipped_set_index=equipped_slot,
        message=(
            "Hypixel did not return saved wardrobe sets (wardrobe_contents). "
            "Showing the armor currently equipped in-game only."
        ),
    )


def _parse_wardrobe_blob(raw: Any, parse_errors: list[str]) -> list[InventoryPage]:
    encoded = extract_encoded_data(raw)
    if encoded is None:
        return []
    try:
        stacks = [_enrich_stack(stack) for stack in parse_inventory_blob(encoded)]
    except (ValueError, RuntimeError) as exc:
        parse_errors.append(str(exc))
        return []
    return build_wardrobe_pages_from_blob(stacks)


def _parse_wardrobe_entry(key: str, entry: Any, parse_errors: list[str]) -> list[InventoryPage]:
    encoded = extract_encoded_data(entry)
    if encoded is None:
        return []
    try:
        stacks = [_enrich_stack(stack) for stack in parse_inventory_blob(encoded)]
    except (ValueError, RuntimeError) as exc:
        parse_errors.append(str(exc))
        return []
    page_index = parse_storage_key_index(key, fallback=0)
    return [build_wardrobe_page(index=page_index, stacks=stacks)]


def _iter_dict_entries(raw: Any, *, kind: str) -> list[tuple[str, Any]]:
    if not isinstance(raw, dict):
        return []
    entries: list[tuple[str, Any]] = []
    for key, value in raw.items():
        if classify_storage_key(str(key)) == kind:
            entries.append((str(key), value))
    entries.sort(key=lambda item: parse_storage_key_index(item[0], fallback=0))
    return entries


def _parse_paged_dict_storage(
    *,
    spec_id: str,
    label: str,
    entries: list[tuple[str, Any]],
    page_builder,
    empty_message: str,
) -> InventoryContainer:
    if not entries:
        return InventoryContainer(
            id=spec_id,
            label=label,
            slot_count=0,
            status="empty",
            message=empty_message,
        )

    pages: list[InventoryPage] = []
    parse_errors: list[str] = []

    for key, entry in entries:
        encoded = extract_encoded_data(entry)
        if encoded is None:
            continue
        try:
            stacks = [_enrich_stack(stack) for stack in parse_inventory_blob(encoded)]
        except (ValueError, RuntimeError) as exc:
            parse_errors.append(str(exc))
            continue
        page_index = parse_storage_key_index(key, fallback=len(pages))
        pages.append(page_builder(index=page_index, stacks=stacks))

    if not pages:
        if parse_errors:
            return InventoryContainer(
                id=spec_id,
                label=label,
                slot_count=0,
                status="error",
                message=parse_errors[0],
            )
        return InventoryContainer(
            id=spec_id,
            label=label,
            slot_count=0,
            status="empty",
            message=empty_message,
        )

    pages.sort(key=lambda page: page.index)
    total_slots = sum(page.slot_count for page in pages)
    all_items = [item for page in pages for item in page.items]
    status = "ok" if all_items else "empty"
    message = None if all_items else empty_message
    return InventoryContainer(
        id=spec_id,
        label=label,
        slot_count=total_slots,
        status=status,
        items=all_items,
        pages=pages,
        message=message,
    )


def _enrich_stack(stack: ItemStack) -> ItemStack:
    catalog = get_catalog_item(stack.item_id) if stack.item_id else None
    display_name = stack.display_name
    if catalog:
        display_name = str(catalog.get("name") or display_name)
    elif stack.name:
        display_name = strip_color_codes(stack.name)

    return ItemStack(
        slot=stack.slot,
        item_id=stack.item_id,
        name=stack.name,
        display_name=display_name,
        lore=stack.lore,
        count=stack.count,
    )
