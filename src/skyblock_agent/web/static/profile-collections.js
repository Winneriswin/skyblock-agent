/**
 * Profile collections — in-game category tabs + item icons.
 */
(function () {
  let groups = [];
  let allEntries = [];
  let activeGroupId = "all";
  let lastCollections = null;

  function $(id) {
    return document.getElementById(id);
  }

  function formatNumber(value) {
    if (typeof window.formatNumber === "function") {
      return window.formatNumber(value);
    }
    return String(value ?? 0);
  }

  function getActiveEntries() {
    if (activeGroupId === "all") {
      return allEntries;
    }
    const group = groups.find((entry) => entry.id === activeGroupId);
    return group?.entries || [];
  }

  function renderTabs() {
    const tabsEl = $("collections-tabs");
    if (!tabsEl) return;
    tabsEl.innerHTML = "";

    const tabs = [{ id: "all", label: "All", count: allEntries.length }];
    groups.forEach((group) => {
      tabs.push({ id: group.id, label: group.label, count: group.entry_count });
    });

    tabs.forEach((tab) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `profile-tab${tab.id === activeGroupId ? " active" : ""}`;
      btn.textContent = `${tab.label} (${tab.count})`;
      btn.addEventListener("click", () => {
        activeGroupId = tab.id;
        renderTabs();
        renderActiveGroup();
      });
      tabsEl.appendChild(btn);
    });
  }

  function createIcon(itemId) {
    const wrap = document.createElement("div");
    wrap.className = "collection-icon-wrap";

    const img = document.createElement("img");
    img.className = "collection-icon invslot-image";
    img.alt = "";
    img.loading = "lazy";
    img.dataset.itemId = itemId;
    img.src = window.ItemIcons ? ItemIcons.iconUrl(itemId) : `/api/items/${encodeURIComponent(itemId)}/icon`;
    wrap.appendChild(img);
    return wrap;
  }

  function renderGrid(entries) {
    const listEl = $("collections-list");
    if (!listEl) return;
    listEl.innerHTML = "";

    if (!entries.length) {
      listEl.innerHTML = `<div class="muted">No collections in this category.</div>`;
      return;
    }

    entries.forEach((entry) => {
      const card = document.createElement("div");
      card.className = "collection-item";
      card.title = entry.display_name || entry.item_id;

      card.appendChild(createIcon(entry.item_id));

      const info = document.createElement("div");
      info.className = "collection-info";

      const name = document.createElement("div");
      name.className = "collection-name";
      name.textContent = entry.display_name || entry.item_id;

      const amount = document.createElement("div");
      amount.className = "collection-amount";
      amount.textContent = formatNumber(entry.amount);

      info.appendChild(name);
      info.appendChild(amount);
      card.appendChild(info);
      listEl.appendChild(card);
    });

    if (window.ItemIcons) {
      ItemIcons.refreshImages(listEl);
    }
  }

  function renderActiveGroup() {
    const metaEl = $("collections-meta");
    const entries = getActiveEntries();
    if (metaEl) {
      if (activeGroupId === "all") {
        const total = lastCollections?.total_items || 0;
        metaEl.textContent = `${entries.length} collections · ${formatNumber(total)} total collected`;
      } else {
        const group = groups.find((entry) => entry.id === activeGroupId);
        metaEl.textContent = group
          ? `${group.label} · ${group.entry_count} collections · ${formatNumber(group.total_amount)} collected`
          : "";
      }
    }
    renderGrid(entries);
  }

  function renderBadge(collections) {
    const badge = $("collections-badge");
    if (!badge) return;
    if (!collections?.available) {
      badge.textContent = "No data";
      badge.className = "pill pill-muted";
      return;
    }
    badge.textContent = `${collections.entry_count} collections`;
    badge.className = "pill pill-ok";
  }

  function render(collections) {
    lastCollections = collections;
    groups = collections?.groups || [];
    allEntries = collections?.entries || [];
    activeGroupId = "all";
    renderBadge(collections);

    const listEl = $("collections-list");
    const metaEl = $("collections-meta");
    const tabsEl = $("collections-tabs");

    if (!collections?.available) {
      if (tabsEl) tabsEl.innerHTML = "";
      if (metaEl) metaEl.textContent = "No collection progress in API response.";
      if (listEl) {
        listEl.innerHTML = `<div class="muted">Collections API may be disabled in-game.</div>`;
      }
      return;
    }

    renderTabs();
    renderActiveGroup();
  }

  function refreshIcons() {
    if (lastCollections) {
      renderActiveGroup();
      return;
    }
    const listEl = $("collections-list");
    if (listEl && window.ItemIcons) {
      ItemIcons.refreshImages(listEl);
    }
  }

  function clear() {
    lastCollections = null;
    groups = [];
    allEntries = [];
    activeGroupId = "all";
    renderBadge({ available: false });
    const tabsEl = $("collections-tabs");
    const listEl = $("collections-list");
    const metaEl = $("collections-meta");
    if (tabsEl) tabsEl.innerHTML = "";
    if (metaEl) metaEl.textContent = "";
    if (listEl) listEl.innerHTML = `<div class="muted">Look up a player to view collections.</div>`;
  }

  window.ProfileCollections = {
    render,
    clear,
    refreshIcons,
  };
})();
