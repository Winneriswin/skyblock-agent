/**
 * Global item icon texture mode: official SkyBlock icons vs vanilla Minecraft materials.
 */
(function () {
  const STORAGE_KEY = "skyblock-agent-icon-texture";
  const listeners = new Set();

  let mode = localStorage.getItem(STORAGE_KEY) || "official";
  if (mode !== "official" && mode !== "vanilla") {
    mode = "official";
  }

  function getMode() {
    return mode;
  }

  function setMode(next) {
    if (next !== "official" && next !== "vanilla") return;
    if (next === mode) return;
    mode = next;
    localStorage.setItem(STORAGE_KEY, mode);
    listeners.forEach((listener) => listener(mode));
  }

  function subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  function iconUrl(itemId) {
    const key = itemId ? String(itemId).trim().toUpperCase() : "";
    if (!key) return "";
    const texture = mode === "vanilla" ? "vanilla" : "official";
    return `/api/items/${encodeURIComponent(key)}/icon?texture=${texture}`;
  }

  function refreshImages(root) {
    const scope = root || document;
    scope.querySelectorAll("img.invslot-image[data-item-id]").forEach((img) => {
      const itemId = img.dataset.itemId;
      if (!itemId) return;
      img.src = iconUrl(itemId);
    });
  }

  window.ItemIcons = {
    getMode,
    setMode,
    subscribe,
    iconUrl,
    refreshImages,
  };
})();
