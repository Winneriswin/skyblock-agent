let activeView = "profile";
let profileRendered = false;

const pillClass = {
  ok: "pill-ok",
  empty: "pill-empty",
  missing: "pill-missing",
  hidden: "pill-hidden",
};

function $(id) {
  return document.getElementById(id);
}

function getNavItems() {
  return document.querySelectorAll(".nav-item[data-view]");
}

function showStatus(message, isError = false) {
  const statusEl = $("status");
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.classList.remove("hidden", "error");
  statusEl.classList.toggle("error", isError);
}

function hideStatus() {
  $("status")?.classList.add("hidden");
}

function formatNumber(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}
window.formatNumber = formatNumber;

function switchView(view) {
  activeView = view;
  getNavItems().forEach((item) => {
    item.classList.toggle("active", item.dataset.view === view);
  });

  $("profile-topbar")?.classList.toggle("hidden", view !== "profile");
  $("market-topbar")?.classList.toggle("hidden", view !== "market");

  const contentEl = $("content");
  const emptyEl = $("empty");
  const marketEmptyEl = $("market-empty");
  const marketContentEl = $("market-content");
  const rngViewEl = $("rng-view");

  contentEl?.classList.add("hidden");
  emptyEl?.classList.add("hidden");
  marketEmptyEl?.classList.add("hidden");
  marketContentEl?.classList.add("hidden");
  rngViewEl?.classList.add("hidden");
  hideStatus();

  if (view === "profile") {
    if (profileRendered) {
      contentEl?.classList.remove("hidden");
    } else {
      emptyEl?.classList.remove("hidden");
    }
    return;
  }

  if (view === "rng") {
    rngViewEl?.classList.remove("hidden");
    return;
  }

  if (view === "market") {
    marketEmptyEl?.classList.remove("hidden");
    marketContentEl?.classList.add("hidden");
    if (typeof MarketBrowser === "undefined") {
      showStatus("Market UI failed to load. Hard-refresh the page (Ctrl+Shift+R).", true);
      return;
    }
    try {
      MarketBrowser.open();
    } catch (error) {
      showStatus(error.message || "Failed to open market view.", true);
    }
  }
}

function renderSkills(summary) {
  const grid = $("skills-grid");
  const badge = $("skills-badge");
  if (!grid || !badge) return;

  badge.textContent = summary.skills_api_enabled ? "API enabled" : "API disabled";
  badge.className = `pill ${summary.skills_api_enabled ? "pill-ok" : "pill-hidden"}`;

  grid.innerHTML = "";
  for (const skill of summary.skills) {
    const item = document.createElement("div");
    item.className = "skill-item";
    const xp = skill.experience === null ? "—" : `${formatNumber(skill.experience)} XP`;
    item.innerHTML = `<div class="skill-name">${skill.name}</div><div class="skill-xp">${xp}</div>`;
    grid.appendChild(item);
  }
}

function renderSlayers(summary) {
  const list = $("slayers-list");
  if (!list) return;

  list.innerHTML = "";
  const active = summary.slayers.filter((s) => s.xp > 0 || s.level > 0);
  if (!active.length) {
    list.innerHTML = `<div class="muted">No slayer progress detected.</div>`;
    return;
  }
  for (const slayer of active) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.innerHTML = `<span>${slayer.name}</span><span>L${slayer.level} · ${formatNumber(slayer.xp)} XP</span>`;
    list.appendChild(row);
  }
}

function renderImport(importInfo) {
  const timeEl = $("import-time");
  const filesEl = $("import-files");
  if (!timeEl || !filesEl) return;

  timeEl.textContent = importInfo.last_imported_at || "Imported";
  filesEl.innerHTML = "";

  const entries = Object.entries(importInfo.saved_files || {});
  if (!entries.length) {
    filesEl.innerHTML = `<div class="muted">No files saved.</div>`;
    return;
  }

  for (const [label, path] of entries) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.innerHTML = `<span>${label}</span><span class="muted import-path">${path}</span>`;
    filesEl.appendChild(row);
  }
}

function renderRecognition(report) {
  const rateEl = $("recognition-rate");
  const summaryEl = $("recognition-summary");
  if (rateEl) rateEl.textContent = `${Math.round(report.pass_rate * 100)}%`;
  if (summaryEl) {
    summaryEl.textContent = `${report.ok_count}/${report.total_count} fields recognized`;
  }

  const table = $("recognition-table");
  if (!table) return;

  table.innerHTML = "";
  for (const check of report.checks) {
    const row = document.createElement("div");
    row.className = "recognition-row";
    row.innerHTML = `
      <div>
        <div>${check.label}</div>
        <code>${check.path}</code>
      </div>
      <span class="pill ${pillClass[check.status] || "pill-muted"}">${check.status}</span>
      <span class="muted">${check.detail || ""}</span>
    `;
    table.appendChild(row);
  }
}

function renderCollections(collections) {
  if (typeof ProfileCollections !== "undefined") {
    ProfileCollections.render(collections);
  }
}

function renderCatacombs(catacombs) {
  if (typeof ProfileCatacombs !== "undefined") {
    ProfileCatacombs.render(catacombs);
  }
}

function renderProfile(payload) {
  const profile = payload.profile;
  const summary = profile.summary;
  const report = payload.recognition;

  $("player-name").textContent = profile.username;
  $("player-meta").textContent =
    `${summary.cute_name} · ${profile.uuid} · ${summary.game_mode || "normal"}`;
  $("sb-level").textContent = formatNumber(summary.skyblock_level);
  $("profile-count").textContent = profile.available_profiles.length;

  renderSkills(summary);
  renderSlayers(summary);
  if (payload.import) renderImport(payload.import);
  renderRecognition(report);
  if (typeof ProfileInventory !== "undefined") {
    if (payload.inventories) ProfileInventory.render(payload.inventories);
    else ProfileInventory.clear();
  }
  renderCollections(payload.collections);
  renderCatacombs(payload.catacombs);

  profileRendered = true;
  $("empty")?.classList.add("hidden");
  $("content")?.classList.remove("hidden");
}

function renderRecentPlayers(players) {
  const recentPlayersEl = $("recent-players");
  if (!recentPlayersEl) return;

  recentPlayersEl.innerHTML = "";
  if (!players.length) {
    recentPlayersEl.innerHTML = `<div class="muted" style="padding:8px 10px">No imports yet</div>`;
    return;
  }

  const form = $("search-form");
  const usernameInput = $("username");
  const profileInput = $("profile-name");

  for (const player of players.slice(0, 12)) {
    const row = document.createElement("div");
    row.className = "recent-player-row";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "recent-player";
    btn.innerHTML = `${player.username}<small>${player.selected_profile || "—"}</small>`;
    btn.addEventListener("click", () => {
      if (usernameInput) usernameInput.value = player.username;
      if (profileInput) profileInput.value = player.selected_profile || "";
      form?.requestSubmit();
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "recent-player-delete";
    deleteBtn.setAttribute("aria-label", `Remove ${player.username}`);
    deleteBtn.title = "Remove import record";
    deleteBtn.textContent = "×";
    deleteBtn.addEventListener("click", async (event) => {
      event.stopPropagation();
      if (!confirm(`Remove import record for ${player.username}?`)) return;
      try {
        const res = await fetch(`/api/players/${encodeURIComponent(player.username)}`, {
          method: "DELETE",
        });
        if (!res.ok) throw new Error("delete failed");
        await loadRecentPlayers();
      } catch {
        showStatus("Failed to delete player record.", true);
      }
    });

    row.appendChild(btn);
    row.appendChild(deleteBtn);
    recentPlayersEl.appendChild(row);
  }
}

async function loadRecentPlayers() {
  const recentPlayersEl = $("recent-players");
  if (!recentPlayersEl) return;

  try {
    const res = await fetch("/api/players");
    const data = await res.json();
    renderRecentPlayers(data.players || []);
  } catch {
    recentPlayersEl.innerHTML = `<div class="muted" style="padding:8px 10px">Unable to load imports</div>`;
  }
}

async function loadHealth() {
  const pill = $("health-pill");
  if (!pill) return;

  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const parts = [];
    if (data.api_key_configured) {
      parts.push("API key OK");
    } else {
      parts.push(data.message || "API key missing");
    }
    if (data.items_catalog?.available) {
      parts.push(`${data.items_catalog.item_count} items cached`);
    } else {
      parts.push("items: run sync-items");
    }
    if (data.items_icons?.available) {
      parts.push(`${data.items_icons.icon_count} icons`);
    } else if (data.items_catalog?.available) {
      parts.push("icons: run sync-icons");
    }
    pill.textContent = parts.join(" · ");
    pill.className = `pill ${
      data.api_key_configured && data.items_catalog?.available && data.items_icons?.available
        ? "pill-ok"
        : "pill-muted"
    }`;
    if (!data.api_key_configured) {
      showStatus(data.message || "Configure HYPIXEL_API_KEY in .env before lookup.", true);
    } else if (!data.items_catalog?.available && data.items_catalog?.hint) {
      showStatus(data.items_catalog.hint, false);
    } else if (data.items_catalog?.available && !data.items_icons?.available && data.items_icons?.hint) {
      showStatus(data.items_icons.hint, false);
    }
  } catch {
    pill.textContent = "Server unavailable";
    pill.className = "pill pill-missing";
  }
}

function initTextureToggle() {
  const toggle = $("texture-toggle");
  if (!toggle || typeof ItemIcons === "undefined") return;

  const buttons = toggle.querySelectorAll(".texture-btn");

  function syncButtons() {
    const mode = ItemIcons.getMode();
    buttons.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.texture === mode);
    });
  }

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      ItemIcons.setMode(btn.dataset.texture);
    });
  });

  ItemIcons.subscribe(() => {
    syncButtons();
    if (typeof ProfileInventory !== "undefined") {
      ProfileInventory.refreshIcons();
    }
    if (typeof ProfileCollections !== "undefined") {
      ProfileCollections.refreshIcons();
    }
    if (typeof MarketBrowser !== "undefined") {
      MarketBrowser.refreshIcons();
    }
    if (typeof TooltipDebug !== "undefined") {
      TooltipDebug.refreshIcons();
    }
  });

  syncButtons();
}

function initApp() {
  const form = $("search-form");
  const searchBtn = $("search-btn");
  const usernameInput = $("username");
  const profileInput = $("profile-name");

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (activeView !== "profile") {
      switchView("profile");
    }
    hideStatus();
    if (searchBtn) searchBtn.disabled = true;

    const username = usernameInput?.value.trim() || "";
    const profileName = profileInput?.value.trim() || "";
    if (!username) {
      showStatus("Please enter a username.", true);
      if (searchBtn) searchBtn.disabled = false;
      return;
    }

    const params = new URLSearchParams();
    if (profileName) params.set("profile", profileName);

    try {
      showStatus(`Looking up ${username} and importing API data…`);
      const res = await fetch(`/api/lookup/${encodeURIComponent(username)}?${params}`);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Request failed");
      }
      hideStatus();
      renderProfile(data);
      loadRecentPlayers();
    } catch (error) {
      showStatus(error.message || "Failed to lookup player.", true);
    } finally {
      if (searchBtn) searchBtn.disabled = false;
    }
  });

  document.querySelector(".nav")?.addEventListener("click", (event) => {
    const item = event.target.closest(".nav-item[data-view]");
    if (!item) return;
    switchView(item.dataset.view);
  });

  loadHealth();
  loadRecentPlayers();
  initTextureToggle();
  if (typeof TooltipDebug !== "undefined") {
    TooltipDebug.render();
  }
  switchView("profile");
  if (typeof ProfileInventory !== "undefined") {
    ProfileInventory.clear();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}
