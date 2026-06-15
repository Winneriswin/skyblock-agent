const statusEl = document.getElementById("status");
const contentEl = document.getElementById("content");
const emptyEl = document.getElementById("empty");
const form = document.getElementById("search-form");
const searchBtn = document.getElementById("search-btn");
const usernameInput = document.getElementById("username");
const profileInput = document.getElementById("profile-name");
const recentPlayersEl = document.getElementById("recent-players");

const pillClass = {
  ok: "pill-ok",
  empty: "pill-empty",
  missing: "pill-missing",
  hidden: "pill-hidden",
};

function showStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.remove("hidden", "error");
  statusEl.classList.toggle("error", isError);
}

function hideStatus() {
  statusEl.classList.add("hidden");
}

function formatNumber(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function renderSkills(summary) {
  const grid = document.getElementById("skills-grid");
  const badge = document.getElementById("skills-badge");
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
  const list = document.getElementById("slayers-list");
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
  const timeEl = document.getElementById("import-time");
  const filesEl = document.getElementById("import-files");
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
  document.getElementById("recognition-rate").textContent = `${Math.round(report.pass_rate * 100)}%`;
  document.getElementById("recognition-summary").textContent =
    `${report.ok_count}/${report.total_count} fields recognized`;

  const table = document.getElementById("recognition-table");
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

function renderProfile(payload) {
  const profile = payload.profile;
  const summary = profile.summary;
  const report = payload.recognition;

  document.getElementById("player-name").textContent = profile.username;
  document.getElementById("player-meta").textContent =
    `${summary.cute_name} · ${profile.uuid} · ${summary.game_mode || "normal"}`;
  document.getElementById("sb-level").textContent = formatNumber(summary.skyblock_level);
  document.getElementById("profile-count").textContent = profile.available_profiles.length;

  renderSkills(summary);
  renderSlayers(summary);
  if (payload.import) renderImport(payload.import);
  renderRecognition(report);

  emptyEl.classList.add("hidden");
  contentEl.classList.remove("hidden");
}

function renderRecentPlayers(players) {
  recentPlayersEl.innerHTML = "";
  if (!players.length) {
    recentPlayersEl.innerHTML = `<div class="muted" style="padding:8px 10px">No imports yet</div>`;
    return;
  }

  for (const player of players.slice(0, 12)) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "recent-player";
    btn.innerHTML = `${player.username}<small>${player.selected_profile || "—"}</small>`;
    btn.addEventListener("click", () => {
      usernameInput.value = player.username;
      profileInput.value = player.selected_profile || "";
      form.requestSubmit();
    });
    recentPlayersEl.appendChild(btn);
  }
}

async function loadRecentPlayers() {
  try {
    const res = await fetch("/api/players");
    const data = await res.json();
    renderRecentPlayers(data.players || []);
  } catch {
    recentPlayersEl.innerHTML = `<div class="muted" style="padding:8px 10px">Unable to load imports</div>`;
  }
}

async function loadHealth() {
  const pill = document.getElementById("health-pill");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.api_key_configured) {
      pill.textContent = "API key configured";
      pill.className = "pill pill-ok";
    } else {
      pill.textContent = data.message || "API key missing (.env)";
      pill.className = "pill pill-missing";
      showStatus(data.message || "Configure HYPIXEL_API_KEY in .env before lookup.", true);
    }
  } catch {
    pill.textContent = "Server unavailable";
    pill.className = "pill pill-missing";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideStatus();
  searchBtn.disabled = true;

  const username = usernameInput.value.trim();
  const profileName = profileInput.value.trim();
  if (!username) {
    showStatus("Please enter a username.", true);
    searchBtn.disabled = false;
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
    searchBtn.disabled = false;
  }
});

loadHealth();
loadRecentPlayers();
