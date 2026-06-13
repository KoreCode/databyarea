(function () {
  var guides = window.DBA_SERVICE_GUIDES || {};
  var stateNames = {
    "alabama": "Alabama", "alaska": "Alaska", "arizona": "Arizona", "arkansas": "Arkansas",
    "california": "California", "colorado": "Colorado", "connecticut": "Connecticut", "delaware": "Delaware",
    "florida": "Florida", "georgia": "Georgia", "hawaii": "Hawaii", "idaho": "Idaho",
    "illinois": "Illinois", "indiana": "Indiana", "iowa": "Iowa", "kansas": "Kansas",
    "kentucky": "Kentucky", "louisiana": "Louisiana", "maine": "Maine", "maryland": "Maryland",
    "massachusetts": "Massachusetts", "michigan": "Michigan", "minnesota": "Minnesota", "mississippi": "Mississippi",
    "missouri": "Missouri", "montana": "Montana", "nebraska": "Nebraska", "nevada": "Nevada",
    "new-hampshire": "New Hampshire", "new-jersey": "New Jersey", "new-mexico": "New Mexico", "new-york": "New York",
    "north-carolina": "North Carolina", "north-dakota": "North Dakota", "ohio": "Ohio", "oklahoma": "Oklahoma",
    "oregon": "Oregon", "pennsylvania": "Pennsylvania", "rhode-island": "Rhode Island", "south-carolina": "South Carolina",
    "south-dakota": "South Dakota", "tennessee": "Tennessee", "texas": "Texas", "utah": "Utah",
    "vermont": "Vermont", "virginia": "Virginia", "washington": "Washington", "west-virginia": "West Virginia",
    "wisconsin": "Wisconsin", "wyoming": "Wyoming"
  };
  var categoryRoots = {"cost-of-living": true, "utility-costs": true, "property-taxes": true, "insurance-costs": true};

  function titleCaseSlug(slug) {
    return String(slug || "").split("-").filter(Boolean).map(function (part) {
      return part.charAt(0).toUpperCase() + part.slice(1);
    }).join(" ");
  }

  function contextFromPath(pathname) {
    var parts = String(pathname || "").split("/").filter(Boolean);
    var state = "";
    var city = "";
    if (parts.length >= 2 && categoryRoots[parts[0]]) {
      state = parts[1] || "";
      city = parts[2] || "";
    } else if (parts.length >= 1 && stateNames[parts[0]]) {
      state = parts[0] || "";
      city = parts[1] || "";
    }
    return {
      state: state,
      city: city,
      stateName: stateNames[state] || titleCaseSlug(state),
      cityName: titleCaseSlug(city)
    };
  }

  function guideUrl(service, ctx) {
    if (ctx.state && ctx.city) return "/service-guides/" + service + "/" + ctx.state + "/" + ctx.city + "/";
    if (ctx.state) return "/service-guides/" + service + "/" + ctx.state + "/";
    return "/service-guides/" + service + "/";
  }

  function labelFor(ctx) {
    if (ctx.city && ctx.stateName) return ctx.cityName + ", " + ctx.stateName;
    if (ctx.stateName) return ctx.stateName;
    return "your area";
  }

  function buildCards(container, ctx) {
    var services = (container.getAttribute("data-services") || "plumber,electrician,hvac,roofing").split(",");
    var title = container.getAttribute("data-title") || "Local Service Guides";
    var intro = container.getAttribute("data-intro") || "Open a contractor-rate guide tailored to this page's location context.";
    var cards = services.map(function (service) {
      service = service.trim();
      var guide = guides[service];
      if (!guide) return "";
      return '<a class="insight-feature-card" data-service-guide-link data-service="' + service + '" href="' + guideUrl(service, ctx) + '">' +
        '<strong>' + guide.label + '</strong>' +
        '<span>' + guide.range + ' planning range for ' + labelFor(ctx) + '.</span>' +
        '<em>Open guide</em>' +
      '</a>';
    }).join("");
    container.innerHTML =
      '<article class="insight-card insight-wide">' +
        '<h2>' + title + '</h2>' +
        '<p>' + intro + '</p>' +
        '<div class="insight-feature-grid" style="margin-top:12px">' + cards + '</div>' +
      '</article>';
  }

  function enhanceLinks(ctx) {
    document.querySelectorAll("[data-service-guide-link]").forEach(function (link) {
      var service = link.getAttribute("data-service") || link.getAttribute("data-service-guide-link");
      if (!service || !guides[service]) return;
      link.setAttribute("href", guideUrl(service, ctx));
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var ctx = contextFromPath(window.location.pathname);
    document.querySelectorAll("[data-service-guide-module]").forEach(function (container) {
      buildCards(container, ctx);
    });
    enhanceLinks(ctx);
  });
})();
