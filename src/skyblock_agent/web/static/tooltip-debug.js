/**
 * Tooltip debug panel — same render path as Bazaar / Auction House (market-browser.js).
 */
(function () {
  const SAMPLE_BAZAAR = {
    product_id: "ENCHANTED_DIAMOND",
    display_name: "Enchanted Diamond",
    category: "MINING",
    tier: "UNCOMMON",
    sell_price: 1200.5,
    buy_price: 1100,
    spread: 100.5,
    buy_volume: 50000,
    sell_volume: 48000,
  };

  const SAMPLE_AUCTION = {
    item_name: "Aspect of the Dragons",
    item_id: "ASPECT_OF_THE_DRAGONS",
    tier: "LEGENDARY",
    category: "weapon",
    bin: true,
    price: 5000000,
    item_lore:
      "§6Deal §c225% §6damage to mobs.\n§7Strength: §c+100\n§7Critical Damage: §c+50%\n§6§lLEGENDARY SWORD",
  };

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

  /** Copied from market-browser.js renderBazaarCard */
  function renderBazaarCard(product) {
    const tip = ItemTooltips.buildBazaarMinetip(product);
    const slot = ItemTooltips.createInvslot(
      product.display_name || product.product_id,
      tip,
      product.product_id
    );
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

  /** Copied from market-browser.js renderAuctionCard */
  function renderAuctionCard(auction) {
    const tip = ItemTooltips.buildAuctionMinetip(auction);
    const slot = ItemTooltips.createInvslot(auction.item_name, tip, auction.item_id);
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

  function render() {
    const grid = $("tooltip-debug-grid");
    if (!grid || typeof ItemTooltips === "undefined") return;

    grid.innerHTML = [
      '<div class="inventory-debug-label">Bazaar</div>',
      renderBazaarCard(SAMPLE_BAZAAR),
      '<div class="inventory-debug-label">Auction House</div>',
      renderAuctionCard(SAMPLE_AUCTION),
    ].join("");

    if (window.Minetip?.hydrate) {
      Minetip.hydrate(grid);
    }
  }

  function refreshIcons() {
    const grid = $("tooltip-debug-grid");
    if (grid && window.ItemIcons) {
      ItemIcons.refreshImages(grid);
    }
  }

  window.TooltipDebug = {
    render,
    refreshIcons,
  };
})();
