/**
 * Minecraft-style tooltips (vanilla JS port of MediaWiki:Common.js/minetip.js).
 *
 * Wiki usage:
 *   <span class="minetip" data-minetip-title="&6Aspect of the Dragons"
 *         data-minetip-text="&7Damage: &c+225/&7Strength: &c+100"></span>
 *
 * - Formatting: Minecraft color codes with & (or §), e.g. &a, &l
 * - Line breaks in description: / (escape as \/)
 *
 * @see https://hypixel-skyblock.fandom.com/wiki/Hypixel_SkyBlock_Wiki:Style_Manual/UIs
 */
(function () {
  let tooltipEl = null;
  let activeTarget = null;

  function normalizeCodes(text) {
    return String(text || "").replace(/§/g, "&");
  }

  function applyFormatting(text) {
    let html = normalizeCodes(text);
    while (html.match(/&[0-9a-el-o]/i)) {
      html = html.replace(
        /&([0-9a-el-o])(.*?)(&f|$)/gi,
        '<span class="format-$1">$2</span>&f'
      );
    }
    return html.replace(/&f/gi, "");
  }

  function buildTooltipHtml(title, description) {
    let html = `<span class="title">${applyFormatting(title)}&f</span>`;
    if (description) {
      const body = normalizeCodes(description)
        .replace(/\\\//g, "/")
        .replace(/\//g, "<br>");
      html += `<span class="description">${applyFormatting(body)}&f</span>`;
    }
    return html;
  }

  function ensureTooltip() {
    if (!tooltipEl) {
      tooltipEl = document.createElement("div");
      tooltipEl.id = "minetip-tooltip";
      document.body.appendChild(tooltipEl);
    }
    return tooltipEl;
  }

  function positionTooltip(clientX, clientY) {
    if (!tooltipEl) return;

    let top = clientY - 34;
    let left = clientX + 14;
    const width = tooltipEl.offsetWidth;
    const height = tooltipEl.offsetHeight;
    const winWidth = window.innerWidth;
    const winHeight = window.innerHeight;
    const scrollY = window.scrollY;

    if (left + width > winWidth) {
      left -= width + 36;
    }
    if (left < 0) {
      left = 0;
      top += 82;
      if (top + height > scrollY + winHeight) {
        top -= 77 + height;
      }
    } else {
      if (top < scrollY) top = scrollY;
      if (top + height > scrollY + winHeight) {
        top = scrollY + winHeight - height;
      }
    }

    tooltipEl.style.top = `${top}px`;
    tooltipEl.style.left = `${left}px`;
  }

  function hideTooltip() {
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
    }
    activeTarget = null;
  }

  function showTooltip(target, clientX, clientY) {
    let title = target.dataset.minetipTitle;
    const description = target.dataset.minetipText;

    if (title === undefined) {
      title = target.getAttribute("title");
      if (!title) return;
      target.dataset.minetipTitle = title;
    }
    if (title === "0" || title === 0) return;

    target.querySelectorAll("[title]").forEach((el) => el.removeAttribute("title"));
    target.removeAttribute("title");

    const tip = ensureTooltip();
    tip.innerHTML = buildTooltipHtml(title, description);
    activeTarget = target;
    positionTooltip(clientX, clientY);
  }

  function onMouseOver(event) {
    const target = event.target.closest(".minetip");
    if (!target || target === activeTarget) return;
    showTooltip(target, event.clientX, event.clientY);
  }

  function onMouseMove(event) {
    if (!tooltipEl || !activeTarget) return;
    if (!activeTarget.contains(event.target) && event.target !== activeTarget) return;
    positionTooltip(event.clientX, event.clientY);
  }

  function onMouseOut(event) {
    if (!activeTarget) return;
    const left = event.target.closest(".minetip");
    if (left !== activeTarget) return;
    const related = event.relatedTarget;
    if (related && activeTarget.contains(related)) return;
    hideTooltip();
  }

  document.addEventListener("mouseover", onMouseOver, true);
  document.addEventListener("mousemove", onMouseMove, true);
  document.addEventListener("mouseout", onMouseOut, true);

  window.Minetip = {
    hide: hideTooltip,
    buildHtml: buildTooltipHtml,
    applyFormatting,
    normalizeCodes,
  };
})();
