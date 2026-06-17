/**
 * Build Hypixel SkyBlock-style minetip payloads for market/item rows.
 * Format matches wiki Module:Inventory slot/Tooltips (title + / separated lines).
 */

const TIER_COLOR = {
  COMMON: "f",
  UNCOMMON: "a",
  RARE: "9",
  EPIC: "5",
  LEGENDARY: "6",
  MYTHIC: "d",
  SPECIAL: "c",
  VERY_SPECIAL: "c",
  SUPREME: "4",
  ADMIN: "4",
};

function tierColor(tier) {
  return TIER_COLOR[String(tier || "").toUpperCase()] || "7";
}

function formatCoins(value) {
  if (value === null || value === undefined) return null;
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function loreToMinetip(lore) {
  if (!lore) return { title: "", text: "" };
  const parts = String(lore).split("\n").filter(Boolean);
  const title = parts[0] || "";
  const text = parts.slice(1).join("/");
  return { title, text };
}

function buildBazaarMinetip(product) {
  const id = product.product_id || product.id || "Unknown";
  const label = product.display_name || id.replace(/_/g, " ");
  const tc = tierColor(product.tier);
  const title = product.tier ? `&${tc}${label}` : `&7${label}`;
  const lines = [
    product.category ? `&7Category: &f${product.category}` : null,
    product.tier ? `&7Tier: &f${product.tier}` : null,
    `&7Instant Buy: &6${formatCoins(product.sell_price)} coins`,
    `&7Instant Sell: &6${formatCoins(product.buy_price)} coins`,
    `&7Spread: &e${formatCoins(product.spread)} coins`,
    `&7Buy volume: &f${formatCoins(product.buy_volume)}`,
    `&7Sell volume: &f${formatCoins(product.sell_volume)}`,
    `&8${id}`,
    "&9&lBAZAAR PRODUCT",
  ].filter(Boolean);
  return { title, text: lines.join("/") };
}

function buildCatalogItemMinetip(item) {
  const tc = tierColor(item.tier);
  const name = item.name || item.id;
  const title = `&${tc}${name}`;
  const lines = [];
  if (item.category) lines.push(`&7Category: &f${item.category}`);
  if (item.npc_sell_price != null) {
    lines.push(`&7NPC Sell: &6${formatCoins(item.npc_sell_price)} coins`);
  }
  if (item.material) lines.push(`&7Material: &8${item.material}`);
  lines.push(`&8${item.id}`);
  if (item.tier) lines.push(`&${tc}&l${item.tier}`);
  return { title, text: lines.join("/") };
}

function buildAuctionMinetip(auction) {
  if (auction.item_lore) {
    const parsed = loreToMinetip(auction.item_lore.replace(/§/g, "&"));
    const lines = [];
    if (auction.bin) lines.push("&7Type: &aBuy It Now");
    else lines.push("&7Type: &eAuction");
    lines.push(`&7Price: &6${formatCoins(auction.price)} coins`);
    if (auction.category) lines.push(`&7Category: &f${auction.category}`);
    if (auction.tier) lines.push(`&7Tier: &f${auction.tier}`);
    const extra = lines.join("/");
    return {
      title: parsed.title || `&f${auction.item_name}`,
      text: parsed.text ? `${parsed.text}/${extra}` : extra,
    };
  }

  const tc = tierColor(auction.tier);
  const title = `&${tc}${auction.item_name}`;
  const lines = [
    auction.bin ? "&7Type: &aBuy It Now" : "&7Type: &eAuction",
    `&7Price: &6${formatCoins(auction.price)} coins`,
  ];
  if (auction.category) lines.push(`&7Category: &f${auction.category}`);
  if (auction.tier) lines.push(`&${tc}&l${auction.tier}`);
  return { title, text: lines.join("/") };
}

function applyMinetip(element, payload) {
  element.classList.add("minetip");
  element.dataset.minetipTitle = payload.title;
  element.dataset.minetipText = payload.text;
}

function createInvslot(label, payload, itemId) {
  const slot = document.createElement("span");
  slot.className = "invslot minetip";
  slot.dataset.minetipTitle = payload.title;
  slot.dataset.minetipText = payload.text;

  const item = document.createElement("span");
  item.className = "invslot-item";

  const fallbackText = (label || itemId || "?").slice(0, 2).toUpperCase();
  const iconKey = itemId ? String(itemId).trim().toUpperCase() : "";

  if (iconKey) {
    const img = document.createElement("img");
    img.className = "invslot-image";
    img.alt = label || iconKey;
    img.loading = "lazy";
    img.decoding = "async";
    img.src = `/api/items/${encodeURIComponent(iconKey)}/icon`;
    img.addEventListener("error", () => {
      img.remove();
      const icon = document.createElement("span");
      icon.className = "invslot-icon";
      icon.textContent = fallbackText;
      item.appendChild(icon);
    });
    item.appendChild(img);
  } else {
    const icon = document.createElement("span");
    icon.className = "invslot-icon";
    icon.textContent = fallbackText;
    item.appendChild(icon);
  }

  slot.appendChild(item);
  return slot;
}

window.ItemTooltips = {
  tierColor,
  buildBazaarMinetip,
  buildCatalogItemMinetip,
  buildAuctionMinetip,
  applyMinetip,
  createInvslot,
};
