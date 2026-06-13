(function () {
  const CONFIG_URL = "/data/monetization_config.json";

  function pageContext() {
    const parts = window.location.pathname.split("/").filter(Boolean);
    const ctx = { path: window.location.pathname, service: "", state: "", city: "", project: "" };
    if (parts[0] === "service-guides") {
      ctx.service = parts[1] || "";
      ctx.state = parts[2] || "";
      if (parts.length >= 5) {
        ctx.city = parts[3] || "";
        ctx.project = parts[4] || "";
      } else if (parts.length === 4) {
        ctx.project = parts[3] || "";
      }
    } else if (parts[0] === "insurance-costs") {
      ctx.service = "insurance";
      ctx.state = parts[1] || "";
      ctx.city = parts[2] || "";
    } else if (parts[0] === "utility-costs" || parts[0] === "utility-cost") {
      ctx.service = "utility";
      ctx.state = parts[1] || "";
      ctx.city = parts[2] || "";
    } else if (parts.length >= 2) {
      ctx.state = parts[0] || "";
      ctx.city = parts[1] || "";
    }
    return ctx;
  }

  function matchesList(list, value) {
    if (!Array.isArray(list) || list.length === 0) return true;
    return list.indexOf("*") !== -1 || (!!value && list.indexOf(value) !== -1);
  }

  function partnerForSlot(config, slotName, ctx) {
    return (config.partners || [])
      .filter(function (partner) {
        return partner.enabled !== false &&
          Array.isArray(partner.slots) &&
          partner.slots.indexOf(slotName) !== -1 &&
          matchesList(partner.services, ctx.service) &&
          matchesList(partner.states, ctx.state) &&
          matchesList(partner.cities, ctx.city) &&
          matchesList(partner.projects, ctx.project);
      })
      .sort(function (a, b) { return (b.priority || 0) - (a.priority || 0); })[0];
  }

  function trackClick(config, payload) {
    if (!config.tracking_enabled) return;
    const endpoint = config.tracking_endpoint || "/api/monetization/event";
    const body = JSON.stringify(Object.assign({
      event: "monetization_click",
      path: window.location.pathname,
      ts: new Date().toISOString()
    }, payload));
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }));
        return;
      }
      fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true }).catch(function () {});
    } catch (err) {}
  }

  function renderPartnerSlot(node, config, slotName, ctx) {
    const slotConfig = (config.slots || {})[slotName] || {};
    const partner = partnerForSlot(config, slotName, ctx);
    const title = (partner && partner.title) || slotConfig.fallback_title || "Compare local options";
    const description = (partner && partner.description) || slotConfig.fallback_description || "Use this planning data before comparing providers.";
    const url = (partner && partner.url) || slotConfig.fallback_url || "/contact/";
    const label = (partner && partner.cta_label) || "Compare Options";
    const partnerId = (partner && partner.id) || "fallback";

    node.classList.add("monetization-slot", "monetization-cta");
    node.innerHTML = [
      '<span class="monetization-label">Sponsored option</span>',
      '<div class="monetization-copy">',
      '<strong>' + escapeHtml(title) + '</strong>',
      '<p>' + escapeHtml(description) + '</p>',
      '</div>',
      '<a class="monetization-button" data-monetization-click href="' + escapeAttr(url) + '" rel="sponsored nofollow">' + escapeHtml(label) + '</a>'
    ].join("");
    const link = node.querySelector("[data-monetization-click]");
    if (link) {
      link.addEventListener("click", function () {
        trackClick(config, { slot: slotName, partner_id: partnerId, service: ctx.service, state: ctx.state, city: ctx.city, project: ctx.project });
      });
    }
  }

  function renderAdSlot(node, config, slotName) {
    if (!config.display_ads_enabled || !config.adsense || !config.adsense.enabled) return;
    const slotConfig = (config.slots || {})[slotName] || {};
    const adSlot = slotConfig.adsense_slot || (config.adsense.slots || {})[slotName] || "";
    if (!config.adsense.client || !adSlot) return;
    node.classList.add("monetization-slot", "monetization-ad");
    node.innerHTML = '<span class="monetization-label">Advertisement</span><ins class="adsbygoogle" style="display:block" data-ad-client="' +
      escapeAttr(config.adsense.client) + '" data-ad-slot="' + escapeAttr(adSlot) + '" data-ad-format="auto" data-full-width-responsive="true"></ins>';
    try {
      window.adsbygoogle = window.adsbygoogle || [];
      window.adsbygoogle.push({});
    } catch (err) {}
  }

  function renderSlots(config) {
    if (!config.enabled) return;
    const ctx = pageContext();
    document.querySelectorAll("[data-monetization-slot]").forEach(function (node) {
      const slotName = node.getAttribute("data-monetization-slot") || "";
      const slotConfig = (config.slots || {})[slotName] || {};
      if (slotConfig.enabled === false) return;
      if (slotConfig.kind === "adsense") {
        renderAdSlot(node, config, slotName);
      } else {
        renderPartnerSlot(node, config, slotName, ctx);
      }
    });
  }

  function insertDisclosure(config) {
    if (!config.enabled || !config.affiliate_disclosure_enabled || !config.disclosure) return;
    if (document.querySelector("[data-affiliate-disclosure]")) return;
    const footer = document.querySelector(".footer");
    if (!footer) return;
    const disclosure = document.createElement("div");
    disclosure.className = "affiliate-disclosure";
    disclosure.setAttribute("data-affiliate-disclosure", "true");
    disclosure.innerHTML = '<strong>' + escapeHtml(config.disclosure.label || "Affiliate disclosure") + ':</strong> ' + escapeHtml(config.disclosure.text || "");
    footer.insertBefore(disclosure, footer.firstChild);
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char];
    });
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, "&#96;");
  }

  fetch(CONFIG_URL, { cache: "no-store" })
    .then(function (response) { return response.ok ? response.json() : null; })
    .then(function (config) {
      if (!config) return;
      insertDisclosure(config);
      renderSlots(config);
    })
    .catch(function () {});
})();
