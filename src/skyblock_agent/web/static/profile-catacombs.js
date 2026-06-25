/**
 * Catacombs stats: class levels, floor completions, S / S+ personal bests.
 */
(function () {
  let modes = [];
  let activeMode = "normal";
  let lastCatacombs = null;

  function $(id) {
    return document.getElementById(id);
  }

  function formatNumber(value) {
    if (typeof window.formatNumber === "function") {
      return window.formatNumber(value);
    }
    return String(value ?? 0);
  }

  function formatDungeonTime(ms) {
    if (ms === null || ms === undefined || Number(ms) <= 0) return "—";
    const totalSeconds = Number(ms) / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds - minutes * 60;
    const secText = minutes > 0 ? seconds.toFixed(2).padStart(5, "0") : seconds.toFixed(2);
    return minutes > 0 ? `${minutes}:${secText}` : `${secText}s`;
  }

  function renderClasses(catacombs) {
    const wrap = $("catacombs-classes");
    if (!wrap) return;
    wrap.innerHTML = "";

    const classes = catacombs?.classes || [];
    if (!classes.length) {
      wrap.innerHTML = `<div class="muted">No class XP recorded.</div>`;
      return;
    }

    classes.forEach((entry) => {
      const card = document.createElement("div");
      card.className = `catacombs-class${entry.selected ? " selected" : ""}`;
      card.innerHTML = `
        <div class="catacombs-class-name">${entry.label}${entry.selected ? " · active" : ""}</div>
        <div class="catacombs-class-level">Lv ${formatNumber(entry.level)}</div>
        <div class="catacombs-class-xp muted">${formatNumber(entry.experience)} XP</div>
      `;
      wrap.appendChild(card);
    });
  }

  function renderModeTabs() {
    const tabsEl = $("catacombs-mode-tabs");
    if (!tabsEl) return;
    tabsEl.innerHTML = "";

    if (modes.length <= 1) {
      tabsEl.classList.add("hidden");
      return;
    }
    tabsEl.classList.remove("hidden");

    modes.forEach((mode) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `profile-tab${mode.mode === activeMode ? " active" : ""}`;
      btn.textContent = `${mode.label} (${mode.total_completions})`;
      btn.addEventListener("click", () => {
        activeMode = mode.mode;
        renderModeTabs();
        renderFloors();
      });
      tabsEl.appendChild(btn);
    });
  }

  function renderFloors() {
    const tableEl = $("catacombs-floors");
    const metaEl = $("catacombs-meta");
    if (!tableEl) return;

    const mode = modes.find((entry) => entry.mode === activeMode) || modes[0];
    if (!mode) {
      tableEl.innerHTML = `<div class="muted">No floor data.</div>`;
      return;
    }

    if (metaEl && lastCatacombs) {
      const levelText =
        lastCatacombs.level !== null && lastCatacombs.level !== undefined
          ? `Catacombs ${formatNumber(lastCatacombs.level)}`
          : "Catacombs —";
      const classText = lastCatacombs.selected_class_label
        ? ` · ${lastCatacombs.selected_class_label}`
        : "";
      const xpText =
        lastCatacombs.experience !== null && lastCatacombs.experience !== undefined
          ? ` · ${formatNumber(lastCatacombs.experience)} XP`
          : "";
      metaEl.textContent = `${levelText}${classText}${xpText} · ${mode.label} · ${mode.total_completions} completions`;
    }

    const floors = mode.floors || [];
    if (!floors.length) {
      tableEl.innerHTML = `<div class="muted">No ${mode.label} floor progress.</div>`;
      return;
    }

    const table = document.createElement("div");
    table.className = "catacombs-table";
    table.innerHTML = `
      <div class="catacombs-row catacombs-head">
        <span>Floor</span>
        <span>Completions</span>
        <span>S PB</span>
        <span>S+ PB</span>
      </div>
    `;

    floors.forEach((floor) => {
      const row = document.createElement("div");
      row.className = "catacombs-row";
      row.innerHTML = `
        <span class="catacombs-floor">${floor.label}</span>
        <span>${formatNumber(floor.completions)}</span>
        <span>${formatDungeonTime(floor.pb_s_ms)}</span>
        <span>${formatDungeonTime(floor.pb_s_plus_ms)}</span>
      `;
      table.appendChild(row);
    });

    tableEl.innerHTML = "";
    tableEl.appendChild(table);
  }

  function renderBadge(catacombs) {
    const badge = $("catacombs-badge");
    if (!badge) return;
    if (!catacombs?.available) {
      badge.textContent = "No data";
      badge.className = "pill pill-muted";
      return;
    }
    badge.textContent =
      catacombs.level !== null && catacombs.level !== undefined
        ? `Cata ${formatNumber(catacombs.level)}`
        : "Available";
    badge.className = "pill pill-ok";
  }

  function render(catacombs) {
    lastCatacombs = catacombs;
    modes = catacombs?.modes || [];
    activeMode = modes[0]?.mode || "normal";

    renderBadge(catacombs);
    renderClasses(catacombs);

    const tableEl = $("catacombs-floors");
    const metaEl = $("catacombs-meta");
    const tabsEl = $("catacombs-mode-tabs");

    if (!catacombs?.available) {
      if (metaEl) metaEl.textContent = catacombs?.message || "No Catacombs data in API response.";
      if (tabsEl) {
        tabsEl.innerHTML = "";
        tabsEl.classList.add("hidden");
      }
      if (tableEl) {
        tableEl.innerHTML = `<div class="muted">Play dungeons or enable API sharing to see stats here.</div>`;
      }
      return;
    }

    renderModeTabs();
    renderFloors();
  }

  function clear() {
    lastCatacombs = null;
    modes = [];
    activeMode = "normal";
    renderBadge({ available: false });
    const metaEl = $("catacombs-meta");
    const tabsEl = $("catacombs-mode-tabs");
    const classesEl = $("catacombs-classes");
    const tableEl = $("catacombs-floors");
    if (metaEl) metaEl.textContent = "";
    if (tabsEl) {
      tabsEl.innerHTML = "";
      tabsEl.classList.add("hidden");
    }
    if (classesEl) classesEl.innerHTML = "";
    if (tableEl) tableEl.innerHTML = `<div class="muted">Look up a player to view Catacombs stats.</div>`;
  }

  window.ProfileCatacombs = {
    render,
    clear,
    formatDungeonTime,
  };
})();
