/**
 * Minecraft-style tooltips (vanilla JS port of MediaWiki:Common.js/minetip.js).
 */
(function () {
  let tooltipEl = null;
  let activeTarget = null;
  let debugPinned = false;
  const payloadStore = new WeakMap();

  function normalizeCodes(text) {
    return String(text || "").replace(/§/g, "&");
  }

  function applyFormatting(text) {
    let html = normalizeCodes(text);
    let guard = 0;
    while (html.match(/&[0-9a-el-o]/i)) {
      if (guard++ > 500) break;
      const prev = html;
      html = html.replace(
        /&([0-9a-el-o])(.*?)(&f|$)/gi,
        '<span class="format-$1">$2</span>&f'
      );
      if (html === prev) break;
    }
    return html.replace(/&f/gi, "");
  }

  function buildTooltipHtml(title, description) {
    let html = `<span class="title">${applyFormatting(title)}</span>`;
    if (description) {
      const body = normalizeCodes(description)
        .replace(/\\\//g, "/")
        .replace(/\//g, "<br>");
      html += `<span class="description">${applyFormatting(body)}</span>`;
    }
    return html;
  }

  function ensureTooltip() {
    if (!tooltipEl || !document.documentElement.contains(tooltipEl)) {
      tooltipEl = document.createElement("div");
      tooltipEl.id = "minetip-tooltip";
      tooltipEl.style.position = "fixed";
      tooltipEl.style.zIndex = "2147483647";
      tooltipEl.style.pointerEvents = "none";
      document.documentElement.appendChild(tooltipEl);
    }
    return tooltipEl;
  }

  function positionTooltip(clientX, clientY) {
    if (!tooltipEl) return;

    const width = tooltipEl.offsetWidth;
    const height = tooltipEl.offsetHeight;
    const winWidth = window.innerWidth;
    const winHeight = window.innerHeight;

    let top = clientY - 34;
    let left = clientX + 14;

    if (left + width > winWidth - 8) {
      left = clientX - width - 14;
    }
    if (left < 8) {
      left = 8;
    }
    if (top < 8) {
      top = clientY + 16;
    }
    if (top + height > winHeight - 8) {
      top = Math.max(8, winHeight - height - 8);
    }

    tooltipEl.style.top = `${top}px`;
    tooltipEl.style.left = `${left}px`;
  }

  function hideTooltip() {
    debugPinned = false;
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
    }
    activeTarget = null;
  }

  function readPayload(target) {
    const stored = payloadStore.get(target);
    if (stored && stored.title) {
      return stored;
    }

    const attrTitle = target.getAttribute("data-minetip-title");
    if (attrTitle !== null && attrTitle !== "") {
      return {
        title: attrTitle,
        text: target.getAttribute("data-minetip-text") || "",
      };
    }

    if (target.dataset.minetipTitle !== undefined && target.dataset.minetipTitle !== "") {
      return {
        title: target.dataset.minetipTitle,
        text: target.dataset.minetipText || "",
      };
    }

    if (target._minetipTitle) {
      return { title: target._minetipTitle, text: target._minetipText || "" };
    }

    const attrTitleLegacy = target.getAttribute("title");
    if (attrTitleLegacy) {
      return { title: attrTitleLegacy, text: "" };
    }

    return null;
  }

  function bindElement(element, payload) {
    if (!element) return;
    element.classList.add("minetip");
    const title = payload?.title || "";
    const text = payload?.text || "";
    payloadStore.set(element, { title, text });
    element._minetipTitle = title;
    element._minetipText = text;
    if (title.length + text.length <= 6000) {
      element.setAttribute("data-minetip-title", title);
      element.setAttribute("data-minetip-text", text);
    } else {
      element.removeAttribute("data-minetip-title");
      element.removeAttribute("data-minetip-text");
    }
  }

  function hydrate(root) {
    const scope = root && root.querySelectorAll ? root : document;
    const nodes =
      root && root.querySelectorAll
        ? root.querySelectorAll(".minetip")
        : scope.querySelectorAll(".minetip");
    nodes.forEach((element) => {
      if (payloadStore.has(element)) return;
      const title = element.getAttribute("data-minetip-title");
      if (title === null || title === "") return;
      bindElement(element, {
        title,
        text: element.getAttribute("data-minetip-text") || "",
      });
    });
  }

  function showTooltip(target, clientX, clientY) {
    const payload = readPayload(target);
    if (!payload || !payload.title) return false;
    if (payload.title === "0") return false;

    target.querySelectorAll("[title]").forEach((el) => el.removeAttribute("title"));
    target.removeAttribute("title");

    const tip = ensureTooltip();
    tip.innerHTML = buildTooltipHtml(payload.title, payload.text);
    activeTarget = target;
    positionTooltip(clientX, clientY);
    if (tip.offsetWidth === 0) {
      requestAnimationFrame(() => positionTooltip(clientX, clientY));
    }
    return true;
  }

  function resolveTarget(target) {
    if (target === undefined || target === null || target === "") {
      return (
        document.querySelector("#inventory-grid .minetip") ||
        document.querySelector("#tooltip-debug-grid .minetip") ||
        document.querySelector(".minetip")
      );
    }
    if (typeof target === "number") {
      return document.querySelectorAll(".minetip")[target] || null;
    }
    if (typeof target === "string") {
      return document.querySelector(target);
    }
    if (target.nodeType === 1) {
      return target;
    }
    return null;
  }

  /** Console: showTip() | showTip(0) | showTip('.inventory-slot.minetip') */
  function forceShow(target, x, y) {
    const el = resolveTarget(target);
    if (!el) {
      console.warn("[Minetip] No .minetip target found.", target);
      return false;
    }
    if (!payloadStore.has(el)) {
      const payload = readPayload(el);
      if (payload?.title) {
        bindElement(el, payload);
      }
    }
    const rect = el.getBoundingClientRect();
    const cx = x ?? rect.left + rect.width / 2;
    const cy = y ?? rect.top + rect.height / 2;
    debugPinned = true;
    const ok = showTooltip(el, cx, cy);
    if (ok) {
      const payload = readPayload(el);
      const box = tooltipEl?.getBoundingClientRect();
      console.info("[Minetip] forced tooltip", {
        target: el,
        title: payload?.title,
        textLength: (payload?.text || "").length,
        rect: box
          ? { top: box.top, left: box.left, width: box.width, height: box.height }
          : null,
      });
    } else {
      debugPinned = false;
      console.warn("[Minetip] Target has no tooltip payload.", el);
    }
    return ok;
  }

  /** Console: showTipRaw('&6Hyperion', '&7Damage: &c+359') */
  function forceShowRaw(title, text, x, y) {
    if (!title) {
      console.warn("[Minetip] title is required");
      return false;
    }
    hideTooltip();
    debugPinned = true;
    const tip = ensureTooltip();
    tip.innerHTML = buildTooltipHtml(title, text || "");
    activeTarget = null;
    const cx = x ?? window.innerWidth / 2;
    const cy = y ?? window.innerHeight / 3;
    positionTooltip(cx, cy);
    if (tip.offsetWidth === 0) {
      requestAnimationFrame(() => positionTooltip(cx, cy));
    }
    console.info("[Minetip] forced raw tooltip", { title, textLength: (text || "").length });
    return true;
  }

  function forceHide() {
    hideTooltip();
    console.info("[Minetip] tooltip hidden");
  }

  function debugList(limit = 20) {
    const nodes = document.querySelectorAll(".minetip");
    const rows = Array.from(nodes, (el, index) => {
      const payload = readPayload(el);
      return {
        index,
        title: payload?.title || "(empty)",
        textLength: (payload?.text || "").length,
        tag: el.tagName.toLowerCase(),
        classes: el.className,
        id: el.id || null,
      };
    }).slice(0, limit);
    console.table(rows);
    console.info(`[Minetip] ${nodes.length} total .minetip elements. Use showTip(n) with index.`);
    return rows;
  }

  function debugInspect() {
    const tip = document.getElementById("minetip-tooltip");
    if (!tip) {
      console.warn("[Minetip] #minetip-tooltip not in DOM. Run showTip() first.");
      return null;
    }
    const rect = tip.getBoundingClientRect();
    const style = window.getComputedStyle(tip);
    const info = {
      inDom: document.documentElement.contains(tip),
      rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
      display: style.display,
      visibility: style.visibility,
      opacity: style.opacity,
      zIndex: style.zIndex,
      position: style.position,
      scrollY: window.scrollY,
      debugPinned,
    };
    console.info("[Minetip] inspect", info);
    return info;
  }

  function debugHelp() {
    console.info(`[Minetip] Tooltip debug commands (browser console):

  showTip()                         — force first inventory/debug slot
  showTip(0)                        — force by index (see listTips())
  showTip('.inventory-slot.minetip') — force by CSS selector
  showTipRaw('&6Hyperion', '&7...')  — force custom text (Minecraft & codes)
  hideTip()                         — close pinned tooltip
  listTips()                        — table of all .minetip on page
  inspectTip()                      — log #minetip-tooltip position/size

Pinned tooltips ignore mouse-out until hideTip().`);
  }

  function findMinetip(node) {
    if (!node || typeof node.closest !== "function") return null;
    return node.closest(".minetip");
  }

  function onMouseOver(event) {
    const target = findMinetip(event.target);
    if (!target) return;
    if (target === activeTarget) return;
    showTooltip(target, event.clientX, event.clientY);
  }

  function onMouseMove(event) {
    if (!tooltipEl || !activeTarget) return;
    if (!activeTarget.contains(event.target) && event.target !== activeTarget) return;
    positionTooltip(event.clientX, event.clientY);
  }

  function onMouseOut(event) {
    if (debugPinned) return;
    if (!activeTarget) return;
    if (!activeTarget.contains(event.target)) return;
    const related = event.relatedTarget;
    if (related && activeTarget.contains(related)) return;
    hideTooltip();
  }

  document.addEventListener("mouseover", onMouseOver, true);
  document.addEventListener("mousemove", onMouseMove, true);
  document.addEventListener("mouseout", onMouseOut, true);

  window.Minetip = {
    bindElement,
    hydrate,
    hide: hideTooltip,
    forceShow,
    forceShowRaw,
    forceHide,
    debugList,
    debugInspect,
    debugHelp,
    buildHtml: buildTooltipHtml,
    applyFormatting,
    normalizeCodes,
  };

  window.showTip = forceShow;
  window.showTipRaw = forceShowRaw;
  window.hideTip = forceHide;
  window.listTips = debugList;
  window.inspectTip = debugInspect;
  window.tipHelp = debugHelp;
})();
