/**
 * Profile inventory grids (official SkyBlock container names).
 */
(function () {
  let containers = [];
  let activeId = null;
  let lastInventories = null;
  const activePageByContainer = new Map();

  const ARMOR_LABELS = ["Helmet", "Chestplate", "Leggings", "Boots"];
  const EQUIPMENT_LABELS = ["Necklace", "Cloak", "Belt", "Gloves"];
  const PLAYER_MAIN_SLOTS = 27;
  const PLAYER_HOTBAR_SLOTS = 9;
  const PLAYER_MAIN_START = 9;

  function $(id) {
    return document.getElementById(id);
  }

  function findEquippedPageIndex(container) {
    if (container.id !== "wardrobe" || typeof container.equipped_set_index !== "number") {
      return -1;
    }
    const pages = container.pages || [];
    return pages.findIndex((page) => page.index === container.equipped_set_index);
  }

  function getActivePageIndex(container) {
    if (!container?.pages?.length) return 0;
    const stored = activePageByContainer.get(container.id);
    if (stored !== undefined && stored < container.pages.length) {
      return stored;
    }
    const equippedPageIndex = findEquippedPageIndex(container);
    if (equippedPageIndex >= 0) {
      return equippedPageIndex;
    }
    return 0;
  }

  function setActivePageIndex(containerId, pageIndex) {
    activePageByContainer.set(containerId, pageIndex);
  }

  function renderTabs() {
    const tabsEl = $("inventory-tabs");
    if (!tabsEl) return;
    tabsEl.innerHTML = "";

    containers.forEach((container) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `profile-tab${container.id === activeId ? " active" : ""}`;
      btn.textContent = container.label;
      btn.addEventListener("click", () => {
        activeId = container.id;
        renderTabs();
        renderActiveContainer();
      });
      tabsEl.appendChild(btn);
    });
  }

  function renderPageControls(container, pageIndex) {
    const pagesEl = $("inventory-pages");
    if (!pagesEl) return;

    const pages = container.pages || [];
    if (pages.length <= 1) {
      pagesEl.classList.add("hidden");
      pagesEl.innerHTML = "";
      return;
    }

    pagesEl.classList.remove("hidden");
    pagesEl.innerHTML = "";

    const prev = document.createElement("button");
    prev.type = "button";
    prev.className = "inventory-page-btn";
    prev.textContent = "‹";
    prev.disabled = pageIndex <= 0;
    prev.addEventListener("click", () => {
      setActivePageIndex(container.id, pageIndex - 1);
      renderActiveContainer();
    });

    const label = document.createElement("span");
    label.className = "inventory-page-label";
    const page = pages[pageIndex];
    const equippedIndex = container.equipped_set_index;
    const isEquippedSet =
      container.id === "wardrobe" &&
      typeof equippedIndex === "number" &&
      page.index === equippedIndex;
    label.textContent = `${page.label} · ${page.filled_slots}/${page.slot_count}${
      isEquippedSet ? " · Equipped" : ""
    }`;

    const next = document.createElement("button");
    next.type = "button";
    next.className = "inventory-page-btn";
    next.textContent = "›";
    next.disabled = pageIndex >= pages.length - 1;
    next.addEventListener("click", () => {
      setActivePageIndex(container.id, pageIndex + 1);
      renderActiveContainer();
    });

    pagesEl.appendChild(prev);
    pagesEl.appendChild(label);
    pagesEl.appendChild(next);
  }

  function appendItemSlot(cell, item) {
    if (!item || !window.ItemTooltips) return;
    cell.removeAttribute("title");
    const tip = ItemTooltips.buildItemStackMinetip(item);
    ItemTooltips.bindMinetip(cell, tip);
    const label = item.display_name || item.item_id || "?";
    const slotEl = ItemTooltips.createInvslot(label, tip, item.item_id, { minetip: false });
    cell.appendChild(slotEl);
    if (item.count > 1) {
      const count = document.createElement("span");
      count.className = "invslot-stacksize";
      count.textContent = String(item.count);
      slotEl.querySelector(".invslot-item")?.appendChild(count);
    }
  }

  function hydrateGridTooltips(gridEl) {
    if (window.Minetip?.hydrate) {
      Minetip.hydrate(gridEl);
    }
  }

  function renderGrid(container, view) {
    const gridEl = $("inventory-grid");
    if (!gridEl) return;

    const itemsBySlot = new Map(
      (view.items || []).map((item) => [Number(item.slot), item])
    );
    gridEl.innerHTML = "";

    if (container.layout === "armor_equipment") {
      gridEl.className = "inventory-grid inventory-armor-equipment";
      for (let row = 0; row < 4; row += 1) {
        const armorCell = document.createElement("div");
        armorCell.className = "inventory-slot";
        const armorItem = itemsBySlot.get(row);
        if (!armorItem) {
          armorCell.title = ARMOR_LABELS[row] || "Armor";
        }
        appendItemSlot(armorCell, armorItem);
        gridEl.appendChild(armorCell);

        const gap = document.createElement("div");
        gap.className = "armor-equipment-gap";
        gridEl.appendChild(gap);

        const equipCell = document.createElement("div");
        equipCell.className = "inventory-slot";
        const equipItem = itemsBySlot.get(row + 4);
        if (!equipItem) {
          equipCell.title = EQUIPMENT_LABELS[row] || "Equipment";
        }
        appendItemSlot(equipCell, equipItem);
        gridEl.appendChild(equipCell);
      }
      hydrateGridTooltips(gridEl);
      return;
    }

    if (container.layout === "armor_column") {
      gridEl.className = "inventory-grid inventory-armor-column";
      for (let row = 0; row < 4; row += 1) {
        const cell = document.createElement("div");
        cell.className = "inventory-slot";
        const piece = itemsBySlot.get(row);
        if (!piece) {
          cell.title = ARMOR_LABELS[row] || "Armor";
        }
        appendItemSlot(cell, piece);
        gridEl.appendChild(cell);
      }
      hydrateGridTooltips(gridEl);
      return;
    }

    if (container.layout === "player_inventory") {
      gridEl.className = "inventory-grid inventory-player";
      gridEl.style.setProperty("--inventory-columns", "9");

      for (let offset = 0; offset < PLAYER_MAIN_SLOTS; offset += 1) {
        const slot = PLAYER_MAIN_START + offset;
        const cell = document.createElement("div");
        cell.className = "inventory-slot";
        appendItemSlot(cell, itemsBySlot.get(slot));
        gridEl.appendChild(cell);
      }

      const divider = document.createElement("div");
      divider.className = "inventory-player-divider";
      divider.setAttribute("aria-hidden", "true");
      gridEl.appendChild(divider);

      for (let slot = 0; slot < PLAYER_HOTBAR_SLOTS; slot += 1) {
        const cell = document.createElement("div");
        cell.className = "inventory-slot";
        appendItemSlot(cell, itemsBySlot.get(slot));
        gridEl.appendChild(cell);
      }
      hydrateGridTooltips(gridEl);
      return;
    }

    gridEl.className = "inventory-grid";
    gridEl.style.setProperty("--inventory-columns", view.slot_count <= 4 ? "4" : "9");

    for (let slot = 0; slot < view.slot_count; slot += 1) {
      const cell = document.createElement("div");
      cell.className = "inventory-slot";
      appendItemSlot(cell, itemsBySlot.get(slot));
      gridEl.appendChild(cell);
    }
    hydrateGridTooltips(gridEl);
  }

  function hideInventoryNotice() {
    const noticeEl = $("inventory-notice");
    if (noticeEl) {
      noticeEl.textContent = "";
      noticeEl.classList.add("hidden");
    }
  }

  function renderActiveContainer() {
    const metaEl = $("inventory-meta");
    const pagesEl = $("inventory-pages");
    const gridEl = $("inventory-grid");
    if (!gridEl || !metaEl) return;

    const container = containers.find((entry) => entry.id === activeId);
    if (!container) {
      gridEl.innerHTML = `<div class="muted">No inventory data.</div>`;
      metaEl.textContent = "";
      hideInventoryNotice();
      if (pagesEl) {
        pagesEl.classList.add("hidden");
        pagesEl.innerHTML = "";
      }
      return;
    }

    if (container.status === "hidden") {
      gridEl.innerHTML = `<div class="muted inventory-message">${container.message || "Inventory API disabled in-game."}</div>`;
      metaEl.textContent = `${container.label} · not available via API`;
      hideInventoryNotice();
      if (pagesEl) {
        pagesEl.classList.add("hidden");
        pagesEl.innerHTML = "";
      }
      return;
    }

    if (container.status === "error") {
      gridEl.innerHTML = `<div class="muted inventory-message">${container.message || "Failed to parse container."}</div>`;
      metaEl.textContent = `${container.label} · parse error`;
      hideInventoryNotice();
      if (pagesEl) {
        pagesEl.classList.add("hidden");
        pagesEl.innerHTML = "";
      }
      return;
    }

    if (container.status === "empty") {
      const message = container.message || "This container is empty.";
      gridEl.innerHTML = `<div class="muted inventory-message">${message}</div>`;
      metaEl.textContent = `${container.label} · empty`;
      hideInventoryNotice();
      if (pagesEl) {
        pagesEl.classList.add("hidden");
        pagesEl.innerHTML = "";
      }
      return;
    }

    const pages = container.pages || [];
    const pageIndex = getActivePageIndex(container);
    const view = pages.length
      ? pages[pageIndex]
      : {
          slot_count: container.slot_count,
          items: container.items || [],
          filled_slots: container.filled_slots,
          label: container.label,
        };

    const noticeEl = $("inventory-notice");
    if (noticeEl) {
      if (container.status === "ok" && container.message) {
        noticeEl.textContent = container.message;
        noticeEl.classList.remove("hidden");
      } else {
        noticeEl.textContent = "";
        noticeEl.classList.add("hidden");
      }
    }

    if (pages.length) {
      renderPageControls(container, pageIndex);
      const pageNote = pages.length === 1 && container.message ? " · partial API data" : "";
      metaEl.textContent = `${container.label} · ${container.filled_slots}/${container.slot_count} items · ${pages.length} pages${pageNote}`;
    } else {
      if (pagesEl) {
        pagesEl.classList.add("hidden");
        pagesEl.innerHTML = "";
      }
      if (container.layout === "armor_equipment") {
        metaEl.textContent = `${container.label} · ${container.filled_slots}/8 slots · Armor (left) · Equipment (right)`;
      } else if (container.layout === "armor_column") {
        const equippedNote =
          typeof container.equipped_set_index === "number"
            ? ` · Equipped: Set ${container.equipped_set_index + 1}`
            : "";
        metaEl.textContent = `${container.label} · ${container.filled_slots}/${view.slot_count} slots · Armor sets${equippedNote}`;
      } else if (container.layout === "player_inventory") {
        metaEl.textContent = `${container.label} · ${container.filled_slots}/36 slots · Main inventory + hotbar`;
      } else {
        metaEl.textContent = `${container.label} · ${container.filled_slots}/${container.slot_count} slots`;
      }
    }

    renderGrid(container, view);
  }

  function renderBadge(inventories) {
    const badge = $("inventory-api-badge");
    if (!badge) return;
    if (!inventories?.inventory_api_enabled) {
      badge.textContent = "API disabled";
      badge.className = "pill pill-missing";
      return;
    }
    const filled = containers.reduce((sum, c) => sum + (c.filled_slots || 0), 0);
    badge.textContent = `${filled} items`;
    badge.className = "pill pill-ok";
  }

  function render(inventories) {
    lastInventories = inventories;
    containers = inventories?.containers || [];
    activeId = containers[0]?.id || null;
    renderBadge(inventories);
    renderTabs();
    renderActiveContainer();
  }

  function refreshIcons() {
    if (lastInventories) {
      render(lastInventories);
      return;
    }
    if (window.ItemIcons) {
      ItemIcons.refreshImages($("inventory-grid"));
    }
  }

  function clear() {
    lastInventories = null;
    containers = [];
    activeId = null;
    activePageByContainer.clear();
    renderBadge({ inventory_api_enabled: false, containers: [] });
    const tabsEl = $("inventory-tabs");
    const gridEl = $("inventory-grid");
    const metaEl = $("inventory-meta");
    const pagesEl = $("inventory-pages");
    if (tabsEl) tabsEl.innerHTML = "";
    if (pagesEl) {
      pagesEl.classList.add("hidden");
      pagesEl.innerHTML = "";
    }
    if (metaEl) metaEl.textContent = "";
    hideInventoryNotice();
    if (gridEl) gridEl.innerHTML = `<div class="muted">Look up a player to view inventories.</div>`;
  }

  window.ProfileInventory = {
    render,
    clear,
    refreshIcons,
  };
})();
