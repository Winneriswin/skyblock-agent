/**
 * Bazaar & Auction House grid browser with placeholder icons and minetip tooltips.
 */
(function () {
  const PAGE_SIZE = 48;

  const state = {
    mode: "bazaar",
    query: "",
    category: "",
    sort: "name",
    binOnly: false,
    bazaarOffset: 0,
    auctionPage: 0,
    loading: false,
    lastMeta: null,
  };

  let els = {};

  function $(id) {
    return document.getElementById(id);
  }

  function escapeAttr(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function formatCoins(value) {
    if (value === null || value === undefined) return "—";
    return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  function formatNumber(value) {
    if (value === null || value === undefined) return "—";
    return Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function formatTimestamp(ms) {
    if (!ms) return "—";
    return new Date(Number(ms)).toLocaleString();
  }

  function setStatus(message, isError = false) {
    const statusEl = $("status");
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.classList.remove("hidden", "error");
    statusEl.classList.toggle("error", isError);
  }

  function clearStatus() {
    const statusEl = $("status");
    if (statusEl) statusEl.classList.add("hidden");
  }

  function updateHero(data) {
    const isBazaar = state.mode === "bazaar";
    $("market-source").textContent = isBazaar ? "Bazaar" : "Auction House";
    $("market-title").textContent = isBazaar ? "Browse Bazaar products" : "Browse Auction House";
    $("market-meta").textContent = isBazaar
      ? `${formatNumber(data.matched_products)} products · sorted by ${state.sort}`
      : `${formatNumber(data.total_auctions)} active · page ${(data.page ?? 0) + 1} of ${data.total_pages ?? 1}`;

    $("market-matched").textContent = formatNumber(
      isBazaar ? data.matched_products : data.matched_auctions
    );
    $("market-total").textContent = formatNumber(
      isBazaar ? data.total_products : data.total_auctions
    );
    $("market-updated").textContent = formatTimestamp(data.last_updated);

    const saved = $("market-saved");
    saved.textContent = data.raw_path ? "Saved locally" : "Live API";
    saved.className = `pill ${data.raw_path ? "pill-ok" : "pill-muted"}`;
  }

  function renderBazaarCard(product) {
    const tip = ItemTooltips.buildBazaarMinetip(product);
    const slot = ItemTooltips.createInvslot(product.display_name || product.product_id, tip);
    const label = product.display_name || product.product_id;
    return `
      <article class="market-card">
        ${slot.outerHTML}
        <div class="market-card-name" title="${escapeAttr(label)}">${label}</div>
        <div class="market-card-price">${formatCoins(product.sell_price)}</div>
        <div class="market-card-sub">Buy ${formatCoins(product.buy_price)}</div>
      </article>
    `;
  }

  function renderAuctionCard(auction) {
    const tip = ItemTooltips.buildAuctionMinetip(auction);
    const slot = ItemTooltips.createInvslot(auction.item_name, tip);
    const badge = auction.bin
      ? '<span class="pill pill-ok market-card-badge">BIN</span>'
      : '<span class="pill pill-muted market-card-badge">Bid</span>';
    return `
      <article class="market-card">
        ${slot.outerHTML}
        ${badge}
        <div class="market-card-name" title="${escapeAttr(auction.item_name)}">${auction.item_name}</div>
        <div class="market-card-price">${formatNumber(auction.price)}</div>
        <div class="market-card-sub">${auction.tier || "—"} · ${auction.category || "—"}</div>
      </article>
    `;
  }

  function renderGrid(data) {
    const grid = els.grid;
    const items =
      state.mode === "bazaar" ? data.products || [] : data.auctions || [];

    if (!items.length) {
      grid.innerHTML = `<div class="muted market-grid-empty">No listings matched your filters.</div>`;
      return;
    }

    const cards = items
      .map((item) =>
        state.mode === "bazaar" ? renderBazaarCard(item) : renderAuctionCard(item)
      )
      .join("");
    grid.innerHTML = cards;
  }

  function renderPagination(data) {
    const bar = els.pagination;
    if (state.mode === "bazaar") {
      const page = Math.floor(state.bazaarOffset / PAGE_SIZE) + 1;
      const totalPages = Math.max(1, Math.ceil((data.matched_products || 0) / PAGE_SIZE));
      bar.innerHTML = `
        <button type="button" class="page-btn" data-action="prev" ${state.bazaarOffset <= 0 ? "disabled" : ""}>Previous</button>
        <span class="page-info">Page ${page} of ${totalPages} · ${formatNumber(data.matched_products)} items</span>
        <button type="button" class="page-btn" data-action="next" ${data.has_more ? "" : "disabled"}>Next</button>
      `;
    } else {
      const page = (data.page ?? 0) + 1;
      const totalPages = data.total_pages ?? 1;
      bar.innerHTML = `
        <button type="button" class="page-btn" data-action="prev" ${page <= 1 ? "disabled" : ""}>Previous</button>
        <span class="page-info">Page ${page} of ${totalPages} · ${formatNumber(data.page_auctions || data.matched_auctions)} on this page</span>
        <button type="button" class="page-btn" data-action="next" ${page >= totalPages ? "disabled" : ""}>Next</button>
      `;
    }

    bar.querySelectorAll(".page-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const action = btn.dataset.action;
        if (state.mode === "bazaar") {
          if (action === "prev" && state.bazaarOffset > 0) {
            state.bazaarOffset = Math.max(0, state.bazaarOffset - PAGE_SIZE);
            loadMarket();
          } else if (action === "next" && data.has_more) {
            state.bazaarOffset += PAGE_SIZE;
            loadMarket();
          }
        } else if (action === "prev" && state.auctionPage > 0) {
          state.auctionPage -= 1;
          loadMarket();
        } else if (action === "next" && page < totalPages) {
          state.auctionPage += 1;
          loadMarket();
        }
      });
    });
  }

  function updateSortOptions() {
    const sortEl = els.sort;
    if (state.mode === "bazaar") {
      sortEl.innerHTML = `
        <option value="name">Sort: Name</option>
        <option value="sell">Sort: Sell price</option>
        <option value="buy">Sort: Buy price</option>
        <option value="spread">Sort: Spread</option>
      `;
    } else {
      sortEl.innerHTML = `
        <option value="price">Sort: Price</option>
        <option value="name">Sort: Name</option>
        <option value="tier">Sort: Tier</option>
      `;
    }
    sortEl.value = state.sort;
  }

  async function loadCategoryOptions() {
    const categoryEl = els.category;
    if (state.mode === "bazaar") {
      let categories = ["ENCHANTMENT", "OTHER"];
      try {
        const res = await fetch("/api/bazaar/categories");
        if (res.ok) {
          const data = await res.json();
          categories = data.categories || categories;
        }
      } catch {
        /* use defaults */
      }
      categoryEl.innerHTML =
        `<option value="">All categories</option>` +
        categories.map((c) => `<option value="${escapeAttr(c)}">${c}</option>`).join("");
    } else {
      const categories = [
        "armor",
        "weapon",
        "accessories",
        "misc",
        "consumables",
        "cosmetic",
        "dyes",
      ];
      categoryEl.innerHTML =
        `<option value="">All categories</option>` +
        categories.map((c) => `<option value="${c}">${c}</option>`).join("");
    }
    categoryEl.value = state.category;
  }

  function syncControls() {
    els.binWrap.classList.toggle("hidden", state.mode !== "auctions");
    els.query.value = state.query;
    els.sort.value = state.sort;
    els.category.value = state.category;
    els.binOnly.checked = state.binOnly;
    updateSortOptions();
  }

  async function loadMarket() {
    if (state.loading) return;
    state.loading = true;
    els.refresh.disabled = true;

    const params = new URLSearchParams();
    if (state.query) params.set("q", state.query);
    if (state.category) params.set("category", state.category);
    params.set("sort", state.sort);
    params.set("limit", String(PAGE_SIZE));

    const endpoint =
      state.mode === "bazaar" ? "/api/bazaar" : "/api/auctions";

    if (state.mode === "bazaar") {
      params.set("offset", String(state.bazaarOffset));
    } else {
      params.set("page", String(state.auctionPage));
      if (state.binOnly) params.set("bin_only", "true");
    }

    try {
      setStatus(
        `Loading ${state.mode === "bazaar" ? "Bazaar" : "Auction House"}…`
      );
      const res = await fetch(`${endpoint}?${params}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");

      state.lastMeta = data;
      updateHero(data);
      renderGrid(data);
      renderPagination(data);
      clearStatus();

      $("market-empty").classList.add("hidden");
      $("market-content").classList.remove("hidden");
    } catch (error) {
      setStatus(error.message || "Failed to load market data.", true);
    } finally {
      state.loading = false;
      els.refresh.disabled = false;
    }
  }

  function switchMode(mode) {
    state.mode = mode;
    state.query = els.query.value.trim();
    state.category = els.category.value;
    state.binOnly = els.binOnly.checked;

    if (mode === "bazaar") {
      state.sort = ["name", "sell", "buy", "spread"].includes(state.sort)
        ? state.sort
        : "name";
      state.bazaarOffset = 0;
    } else {
      state.sort = ["price", "name", "tier"].includes(state.sort) ? state.sort : "price";
      state.auctionPage = 0;
    }

    els.tabs.forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.market === mode);
    });

    syncControls();
    loadCategoryOptions().then(() => loadMarket());
  }

  function applyFilters() {
    state.query = els.query.value.trim();
    state.category = els.category.value;
    state.sort = els.sort.value;
    state.binOnly = els.binOnly.checked;
    state.bazaarOffset = 0;
    state.auctionPage = 0;
    loadMarket();
  }

  function bindElements() {
    els = {
      tabs: document.querySelectorAll(".market-tab"),
      query: $("market-query"),
      category: $("market-category"),
      sort: $("market-sort"),
      binOnly: $("bin-only"),
      binWrap: $("bin-only-wrap"),
      refresh: $("market-refresh"),
      grid: $("market-grid"),
      pagination: $("market-pagination"),
      form: $("market-browser-form"),
    };
  }

  let initialized = false;

  function initMarketBrowser() {
    if (initialized) return;
    initialized = true;
    bindElements();
    if (!els.grid) return;

    els.tabs.forEach((tab) => {
      tab.addEventListener("click", () => switchMode(tab.dataset.market));
    });

    els.form.addEventListener("submit", (event) => {
      event.preventDefault();
      applyFilters();
    });

    els.sort.addEventListener("change", applyFilters);
    els.category.addEventListener("change", applyFilters);
    els.binOnly.addEventListener("change", applyFilters);
    els.refresh.addEventListener("click", () => loadMarket());

    syncControls();
    loadCategoryOptions();
  }

  window.MarketBrowser = {
    init: initMarketBrowser,
    open: () => {
      initMarketBrowser();
      if (!state.lastMeta) {
        switchMode("bazaar");
      }
    },
    refresh: loadMarket,
  };
})();
