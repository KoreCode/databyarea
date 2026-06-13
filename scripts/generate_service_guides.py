#!/usr/bin/env python3
"""Generate static high-intent service guide pages.

Outputs:
- /service-guides/
- /service-guides/{service}/
- /service-guides/{service}/{state}/
- /service-guides/{service}/{state}/{city}/ for existing canonical city pages
- /service-guides/{service}/{state}/{city}/{project}/ for detailed high-intent project pages
"""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from service_guide_data import build_service_guide_context
except ImportError:  # pragma: no cover - package import fallback
    from scripts.service_guide_data import build_service_guide_context

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://databyarea.com"
OUT_ROOT = ROOT / "service-guides"
TEMPLATE_ROOT = ROOT / "templates"
HIGH_INTENT_TEMPLATE = TEMPLATE_ROOT / "high-intent-service-guide.html"

US_STATES = {
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
    "wisconsin": "Wisconsin", "wyoming": "Wyoming",
}

SERVICE_GUIDES: dict[str, dict[str, Any]] = {
    "plumber": {
        "label": "Plumber Rates",
        "service": "plumber",
        "unit": "hour",
        "range": "$85-$165/hr",
        "low": "$85",
        "high": "$165",
        "project_examples": ["Leak repair or drain clearing", "Fixture and faucet replacement", "Water heater installation", "Pipe replacement or rerouting"],
        "drivers": ["Emergency versus scheduled service", "Pipe material and accessibility", "Local plumbing codes", "Fixture quality and replacement scope"],
        "related": ["water-heater", "electrician", "hvac"],
    },
    "electrician": {
        "label": "Electrician Rates",
        "service": "electrician",
        "unit": "hour",
        "range": "$90-$175/hr",
        "low": "$90",
        "high": "$175",
        "project_examples": ["Panel inspection or repair", "Outlet and switch installation", "EV charger installation", "Rewiring and dedicated circuits"],
        "drivers": ["Panel capacity and existing wiring condition", "Permit and inspection requirements", "Circuit complexity", "Material and device quality"],
        "related": ["hvac", "plumber", "water-heater"],
    },
    "hvac": {
        "label": "HVAC Installation",
        "service": "HVAC contractor",
        "unit": "project",
        "range": "$5,500-$14,500",
        "low": "$5,500",
        "high": "$14,500",
        "project_examples": ["Central AC replacement", "Furnace replacement", "Heat pump installation", "Ductwork repair or replacement"],
        "drivers": ["System size and efficiency rating", "Duct condition", "Local climate", "Electrical or permit work"],
        "related": ["electrician", "plumber", "water-heater"],
    },
    "roofing": {
        "label": "Roof Replacement",
        "service": "roofer",
        "unit": "project",
        "range": "$8,000-$24,000",
        "low": "$8,000",
        "high": "$24,000",
        "project_examples": ["Asphalt shingle replacement", "Roof deck repair", "Flashing and ventilation work", "Tear-off and disposal"],
        "drivers": ["Roof size and pitch", "Material choice", "Decking condition", "Storm exposure and local labor demand"],
        "related": ["garage-door", "foundation", "concrete-driveway"],
    },
    "water-heater": {
        "label": "Water Heater Installation",
        "service": "water heater installer",
        "unit": "project",
        "range": "$1,200-$4,500",
        "low": "$1,200",
        "high": "$4,500",
        "project_examples": ["Tank water heater replacement", "Tankless water heater installation", "Expansion tank or valve work", "Vent and gas line adjustments"],
        "drivers": ["Tank versus tankless system", "Fuel type", "Code upgrades", "Access and disposal"],
        "related": ["plumber", "electrician", "hvac"],
    },
    "garage-door": {
        "label": "Garage Door Repair",
        "service": "garage door contractor",
        "unit": "project",
        "range": "$180-$1,800",
        "low": "$180",
        "high": "$1,800",
        "project_examples": ["Spring replacement", "Opener installation", "Panel replacement", "Full door replacement"],
        "drivers": ["Door size and material", "Spring and opener type", "Emergency timing", "Track or panel damage"],
        "related": ["roofing", "foundation", "concrete-driveway"],
    },
    "foundation": {
        "label": "Foundation Repair",
        "service": "foundation repair contractor",
        "unit": "project",
        "range": "$2,500-$18,000",
        "low": "$2,500",
        "high": "$18,000",
        "project_examples": ["Crack repair", "Pier installation", "Basement waterproofing", "Structural stabilization"],
        "drivers": ["Soil movement", "Structural severity", "Water intrusion", "Engineering and permit needs"],
        "related": ["concrete-driveway", "roofing", "garage-door"],
    },
    "concrete-driveway": {
        "label": "Concrete Driveway Cost",
        "service": "concrete contractor",
        "unit": "project",
        "range": "$4,000-$12,000",
        "low": "$4,000",
        "high": "$12,000",
        "project_examples": ["Driveway replacement", "Concrete removal", "Base preparation", "Stamped or reinforced concrete"],
        "drivers": ["Square footage", "Concrete thickness", "Site preparation", "Finish and reinforcement"],
        "related": ["foundation", "garage-door", "roofing"],
    },
}

PROJECT_GUIDES: dict[str, list[dict[str, Any]]] = {
    "plumber": [
        {"slug": "leak-repair", "label": "Leak Repair", "range": "$150-$650", "unit": "repair", "scope": "finding and repairing a visible supply or drain leak"},
        {"slug": "drain-cleaning", "label": "Drain Cleaning", "range": "$125-$500", "unit": "visit", "scope": "clearing a sink, tub, shower, or main-line clog"},
        {"slug": "faucet-replacement", "label": "Faucet Replacement", "range": "$180-$650", "unit": "fixture", "scope": "removing an old faucet and installing a comparable replacement"},
        {"slug": "pipe-replacement", "label": "Pipe Replacement", "range": "$450-$2,500", "unit": "section", "scope": "replacing an accessible damaged or outdated pipe section"},
    ],
    "electrician": [
        {"slug": "new-outlets", "label": "New Outlets", "range": "$175-$650", "unit": "outlet", "scope": "adding one or more standard outlets where wiring access is reasonable"},
        {"slug": "panel-upgrade", "label": "Panel Upgrade", "range": "$1,800-$5,500", "unit": "project", "scope": "upgrading an electrical panel, breakers, labeling, and inspection items"},
        {"slug": "ev-charger-installation", "label": "EV Charger Installation", "range": "$750-$2,800", "unit": "project", "scope": "installing a Level 2 charger circuit and mounting the charger"},
        {"slug": "light-fixture-installation", "label": "Light Fixture Installation", "range": "$150-$900", "unit": "fixture", "scope": "installing or replacing interior or exterior lighting fixtures"},
    ],
    "hvac": [
        {"slug": "ac-replacement", "label": "AC Replacement", "range": "$4,800-$12,000", "unit": "project", "scope": "replacing a central air conditioner with comparable capacity"},
        {"slug": "furnace-replacement", "label": "Furnace Replacement", "range": "$4,200-$10,500", "unit": "project", "scope": "replacing a forced-air furnace and related connections"},
        {"slug": "heat-pump-installation", "label": "Heat Pump Installation", "range": "$6,500-$18,000", "unit": "project", "scope": "installing a heat pump system with required electrical and refrigerant work"},
        {"slug": "ductwork-repair", "label": "Ductwork Repair", "range": "$600-$4,500", "unit": "project", "scope": "repairing, sealing, or replacing sections of ductwork"},
    ],
    "roofing": [
        {"slug": "asphalt-shingle-replacement", "label": "Asphalt Shingle Replacement", "range": "$8,000-$22,000", "unit": "roof", "scope": "tear-off, disposal, underlayment, flashing, and new asphalt shingles"},
        {"slug": "roof-leak-repair", "label": "Roof Leak Repair", "range": "$350-$2,500", "unit": "repair", "scope": "finding and repairing a localized roof leak"},
        {"slug": "flashing-repair", "label": "Flashing Repair", "range": "$300-$1,800", "unit": "repair", "scope": "repairing flashing around chimneys, walls, skylights, or vents"},
        {"slug": "roof-deck-repair", "label": "Roof Deck Repair", "range": "$750-$4,500", "unit": "project", "scope": "repairing damaged roof decking found during roof work"},
    ],
    "water-heater": [
        {"slug": "tank-water-heater-replacement", "label": "Tank Water Heater Replacement", "range": "$1,200-$3,200", "unit": "project", "scope": "removing and replacing a standard tank water heater"},
        {"slug": "tankless-water-heater-installation", "label": "Tankless Water Heater Installation", "range": "$2,500-$7,500", "unit": "project", "scope": "installing a tankless unit with venting, fuel, and code updates"},
        {"slug": "expansion-tank-installation", "label": "Expansion Tank Installation", "range": "$250-$750", "unit": "project", "scope": "adding or replacing a thermal expansion tank"},
        {"slug": "water-heater-code-upgrades", "label": "Water Heater Code Upgrades", "range": "$300-$1,500", "unit": "project", "scope": "updating valves, pan, venting, straps, or related code items"},
    ],
    "garage-door": [
        {"slug": "spring-replacement", "label": "Spring Replacement", "range": "$180-$550", "unit": "repair", "scope": "replacing broken torsion or extension springs"},
        {"slug": "opener-installation", "label": "Opener Installation", "range": "$300-$900", "unit": "project", "scope": "installing a garage door opener and basic controls"},
        {"slug": "panel-replacement", "label": "Panel Replacement", "range": "$350-$1,500", "unit": "panel", "scope": "replacing one or more damaged door panels"},
        {"slug": "full-door-replacement", "label": "Full Door Replacement", "range": "$900-$4,500", "unit": "door", "scope": "removing and replacing the full garage door assembly"},
    ],
    "foundation": [
        {"slug": "crack-repair", "label": "Foundation Crack Repair", "range": "$450-$2,500", "unit": "repair", "scope": "sealing or structurally repairing foundation cracks"},
        {"slug": "pier-installation", "label": "Pier Installation", "range": "$1,200-$3,500", "unit": "pier", "scope": "installing support piers to stabilize settlement"},
        {"slug": "basement-waterproofing", "label": "Basement Waterproofing", "range": "$2,500-$12,000", "unit": "project", "scope": "adding drainage, sealing, sump, or waterproofing measures"},
        {"slug": "structural-stabilization", "label": "Structural Stabilization", "range": "$5,000-$25,000", "unit": "project", "scope": "stabilizing walls, footings, or structural movement"},
    ],
    "concrete-driveway": [
        {"slug": "driveway-replacement", "label": "Driveway Replacement", "range": "$4,000-$12,000", "unit": "driveway", "scope": "removing and replacing a standard concrete driveway"},
        {"slug": "concrete-removal", "label": "Concrete Removal", "range": "$900-$4,000", "unit": "project", "scope": "breaking, hauling, and disposing of old concrete"},
        {"slug": "stamped-concrete", "label": "Stamped Concrete", "range": "$8,000-$20,000", "unit": "project", "scope": "pouring decorative stamped concrete with color or pattern"},
        {"slug": "reinforced-driveway", "label": "Reinforced Driveway", "range": "$5,500-$15,000", "unit": "driveway", "scope": "adding reinforcement, thicker slab, or base upgrades"},
    ],
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def title_case_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part)


def state_city_routes() -> list[tuple[str, str, str]]:
    routes: list[tuple[str, str, str]] = []
    for state_slug, state_name in US_STATES.items():
        state_dir = ROOT / state_slug
        if not state_dir.exists():
            continue
        for child in sorted(state_dir.iterdir(), key=lambda p: p.name):
            if child.name.endswith("-template"):
                continue
            if child.is_dir() and (child / "index.html").exists():
                routes.append((state_slug, state_name, child.name))
    return routes


def service_url(service_slug: str, state_slug: str = "", city_slug: str = "") -> str:
    if state_slug and city_slug:
        return f"/service-guides/{service_slug}/{state_slug}/{city_slug}/"
    if state_slug:
        return f"/service-guides/{service_slug}/{state_slug}/"
    return f"/service-guides/{service_slug}/"


def project_url(service_slug: str, project_slug: str, state_slug: str = "", city_slug: str = "") -> str:
    return f"{service_url(service_slug, state_slug, city_slug)}{project_slug}/"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_template(path: Path, values: dict[str, object]) -> str:
    template = path.read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template


def parse_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def html_list(items: list[str]) -> str:
    return "\n".join(f"<li>{esc(item)}</li>" for item in items)


def api_source_items(source_notes: list[dict[str, str]]) -> str:
    if not source_notes:
        return "<li>No source records were returned for this generation.</li>"
    badges = {"ok": "Used", "missing_key": "Missing key", "error": "Unavailable", "skipped": "Skipped", "no_match": "No match"}
    return "\n".join(
        f"<li><strong>{esc(note.get('name', 'Source'))}:</strong> {esc(badges.get(note.get('status', ''), note.get('status', 'Status')))}. {esc(note.get('detail', ''))}</li>"
        for note in source_notes
    )


def market_signal_items(market_items: list[tuple[str, str]]) -> str:
    return "\n".join(
        f"""<div><strong>{esc(value)}</strong><span>{esc(label)}</span></div>"""
        for label, value in market_items
    )


def page_shell(title: str, desc: str, canonical_path: str, body: str, *, robots: str = "index,follow,max-image-preview:large") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{esc(title)} | DataByArea</title>
  <meta name="description" content="{esc(desc)}" />
  <meta name="robots" content="{esc(robots)}" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="canonical" href="{SITE}{esc(canonical_path)}" />
  <meta property="og:title" content="{esc(title)} | DataByArea" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{SITE}{esc(canonical_path)}" />
  <meta property="og:type" content="article" />
  <meta name="twitter:card" content="summary" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/assets/styles.css" />
</head>
<body class="area-dashboard-page insight-hub-page">
  <a class="skip-link" href="#main-content">Skip to content</a>
  <div class="container area-dashboard-shell">
    <header class="area-top-nav area-home-header">
      <a href="/" class="area-home-brand" aria-label="DataByArea.com home">
        <span class="area-home-logo" aria-hidden="true"><img src="/assets/logo-icon.svg" alt="" width="36" height="36" decoding="async" fetchpriority="high" /></span>
        <span>DataByArea.com</span>
      </a>
      <div class="area-home-actions">
        <a class="area-home-button search" href="/search/">Search Data</a>
        <a class="area-home-login" href="/login/">Log In</a>
        <a class="area-home-button signup" href="/signup/">Sign Up</a>
      </div>
    </header>
    <nav class="insight-topics" aria-label="Insight pages">
      <a class="active" href="/service-guides/">Service Guides</a>
      <a href="/cost-of-living/">Cost of Living</a>
      <a href="/utility-costs/">Utilities</a>
      <a href="/property-taxes/">Property Taxes</a>
      <a href="/insurance-costs/">Insurance</a>
    </nav>
    {body}
    <footer class="footer home-footer">
      <p><strong>Disclaimer:</strong> Contractor and project rates are planning estimates. Exact prices vary by scope, property condition, permits, materials, and contractor availability.</p>
      <p><a href="/about/">About</a> &middot; <a href="/privacy/">Privacy Policy</a> &middot; <a href="/contact/">Contact</a></p>
    </footer>
  </div>
  <script defer src="/assets/version-footer.js"></script>
</body>
</html>
"""


def guide_page(service_slug: str, guide: dict[str, Any], state_slug: str = "", state_name: str = "", city_slug: str = "") -> str:
    city_name = title_case_slug(city_slug)
    location = f"{city_name}, {state_name}" if city_slug else (state_name or "the United States")
    title = f"{guide['label']} in {location}"
    desc = f"{guide['label']} for {location} with project rate ranges, cost drivers, quote checks, and related service guides."
    canonical = service_url(service_slug, state_slug, city_slug)
    breadcrumb = " &rsaquo; ".join(
        part for part in [
            '<a href="/">Home</a>',
            '<a href="/service-guides/">Service Guides</a>',
            f'<a href="{service_url(service_slug)}">{esc(guide["label"])}</a>',
            f'<a href="{service_url(service_slug, state_slug)}">{esc(state_name)}</a>' if state_slug and city_slug else esc(state_name) if state_slug else "",
            esc(city_name) if city_slug else "",
        ] if part
    )
    project_items = "\n".join(f"<li>{esc(item)}</li>" for item in guide["project_examples"])
    driver_items = "\n".join(f"<li>{esc(item)}</li>" for item in guide["drivers"])
    related_cards = "\n".join(
        f"""<a class="insight-feature-card" href="{service_url(rel, state_slug, city_slug)}"><strong>{esc(SERVICE_GUIDES[rel]["label"])}</strong><span>{esc(SERVICE_GUIDES[rel]["range"])} planning range for {esc(location)}.</span><em>Open guide</em></a>"""
        for rel in guide["related"] if rel in SERVICE_GUIDES
    )
    project_cards = "\n".join(
        f"""<a class="insight-feature-card" href="{project_url(service_slug, project['slug'], state_slug, city_slug)}"><strong>{esc(project['label'])}</strong><span>{esc(project['range'])} planning range for {esc(location)}.</span><em>Open project</em></a>"""
        for project in PROJECT_GUIDES.get(service_slug, [])
    )
    body = f"""
    <main id="main-content" class="insight-main">
      <section class="insight-hero" aria-labelledby="service-guide-title">
        <div>
          <div class="insight-breadcrumbs">{breadcrumb}</div>
          <h1 id="service-guide-title">{esc(title)}</h1>
          <p>Use this static service guide to plan {esc(guide['service'])} costs for {esc(location)}. The page is generated ahead of time so internal links, canonical URLs, and SEO signals point at durable service-guide pages.</p>
          <div class="insight-actions">
            <a href="#rate-snapshot">Rates</a>
            <a href="#project-examples">Projects</a>
            <a href="#quote-checks">Quote Checks</a>
            <a href="/service-guides/">All Guides</a>
          </div>
        </div>
        <aside class="insight-panel" id="rate-snapshot" aria-label="{esc(guide['label'])} rate snapshot">
          <h2>Rate Snapshot</h2>
          <div class="insight-panel-grid">
            <div><strong>{esc(guide['range'])}</strong><span>Planning range</span></div>
            <div><strong>{esc(location)}</strong><span>Location context</span></div>
            <div><strong>{esc(guide['unit'])}</strong><span>Estimate basis</span></div>
            <div><strong>2-3</strong><span>Written quotes</span></div>
          </div>
          <p class="insight-source">These ranges are a starting point. FRED, BEA, BLS, Census, and first-party quote data can be layered into this template as the rate model matures.</p>
        </aside>
      </section>

      <section class="insight-grid" aria-label="{esc(title)}">
        <article class="insight-card">
          <span class="insight-label">Low planning point</span>
          <span class="insight-kpi">{esc(guide['low'])}</span>
          <p>Usually assumes straightforward access, standard materials, and scheduled work.</p>
        </article>
        <article class="insight-card">
          <span class="insight-label">High planning point</span>
          <span class="insight-kpi">{esc(guide['high'])}</span>
          <p>Often reflects more complex scope, access issues, upgraded materials, or urgent timing.</p>
        </article>
        <article class="insight-card">
          <span class="insight-label">Location factor</span>
          <span class="insight-kpi">{esc(state_name or 'National')}</span>
          <p>Labor availability, permit rules, travel time, and cost of living can shift local bids.</p>
        </article>
        <article class="insight-card">
          <span class="insight-label">Best next step</span>
          <span class="insight-kpi">Quotes</span>
          <p>Compare written estimates with the same scope, timing, materials, permits, and warranty terms.</p>
        </article>

        <article class="insight-card insight-wide" id="project-examples">
          <h2>Common Project Types</h2>
          <ul class="insight-list" style="margin-top:10px">{project_items}</ul>
        </article>

        <article class="insight-card insight-wide">
          <h2>Detailed Project Guides</h2>
          <div class="insight-feature-grid" style="margin-top:12px">{project_cards}</div>
        </article>

        <article class="insight-card insight-wide">
          <h2>What Moves the Price</h2>
          <ul class="insight-list" style="margin-top:10px">{driver_items}</ul>
        </article>

        <article class="insight-card insight-wide" id="quote-checks">
          <h2>Quote Checks</h2>
          <ul class="insight-list" style="margin-top:10px">
            <li>Ask whether the estimate is hourly, flat-rate, diagnostic-plus-repair, or project based.</li>
            <li>Confirm permits, inspections, disposal, cleanup, and warranty terms in writing.</li>
            <li>Compare the same materials, fixture quality, system size, or repair scope across bids.</li>
            <li>Document what triggers extra charges, emergency fees, travel fees, and change orders.</li>
          </ul>
        </article>

        <article class="insight-card insight-wide">
          <h2>Related Guides</h2>
          <div class="insight-feature-grid" style="margin-top:12px">{related_cards}</div>
        </article>
      </section>
    </main>
"""
    return page_shell(title, desc, canonical, body)


def project_page(
    service_slug: str,
    guide: dict[str, Any],
    project: dict[str, Any],
    state_slug: str = "",
    state_name: str = "",
    city_slug: str = "",
    *,
    use_api: bool = True,
    api_timeout: int = 8,
) -> str:
    city_name = title_case_slug(city_slug)
    location = f"{city_name}, {state_name}" if city_slug else (state_name or "the United States")
    data_context = build_service_guide_context(
        service_slug=service_slug,
        service_label=guide["label"],
        project_label=project["label"],
        project_range=project["range"],
        state_slug=state_slug,
        state_name=state_name,
        city_name=city_name,
        timeout=api_timeout,
        use_api=use_api and bool(state_slug),
    )
    title = f"Cost for {project['label']} in {location}"
    desc = f"{project['label']} cost guide for {location}, including project range, scope, price drivers, quote checks, and related {guide['service']} projects."
    canonical = project_url(service_slug, project["slug"], state_slug, city_slug)
    breadcrumb = " &rsaquo; ".join(
        part for part in [
            '<a href="/">Home</a>',
            '<a href="/service-guides/">Service Guides</a>',
            f'<a href="{service_url(service_slug)}">{esc(guide["label"])}</a>',
            f'<a href="{service_url(service_slug, state_slug)}">{esc(state_name)}</a>' if state_slug else "",
            f'<a href="{service_url(service_slug, state_slug, city_slug)}">{esc(city_name)}</a>' if state_slug and city_slug else "",
            esc(project["label"]),
        ] if part
    )
    driver_items = "\n".join(f"<li>{esc(item)}</li>" for item in guide["drivers"])
    sibling_cards = "\n".join(
        f"""<a class="insight-feature-card" href="{project_url(service_slug, item['slug'], state_slug, city_slug)}"><strong>{esc(item['label'])}</strong><span>{esc(item['range'])} planning range for {esc(location)}.</span><em>Open project</em></a>"""
        for item in PROJECT_GUIDES.get(service_slug, [])
        if item["slug"] != project["slug"]
    )
    return render_template(
        HIGH_INTENT_TEMPLATE,
        {
            "site": SITE,
            "title": esc(title),
            "description": esc(desc),
            "canonical_path": esc(canonical),
            "breadcrumb": breadcrumb,
            "service_label_lower": esc(guide["label"].lower()),
            "project_scope": esc(project["scope"]),
            "project_scope_sentence": f"{esc(project['scope']).capitalize()}.",
            "location": esc(location),
            "project_label": esc(project["label"]),
            "project_range": esc(data_context["adjusted_project_range"]),
            "base_project_range": esc(data_context["base_project_range"]),
            "project_unit": esc(project["unit"]),
            "location_short": esc(city_name or state_name or "National"),
            "back_to_service_url": service_url(service_slug, state_slug, city_slug),
            "driver_items": driver_items,
            "sibling_cards": sibling_cards,
            "data_quality_label": esc(data_context["data_quality_label"]),
            "model_label": esc(data_context["model_label"]),
            "estimate_summary": esc(data_context["estimate_summary"]),
            "updated_at_utc": esc(data_context["updated_at_utc"]),
            "market_signal_items": market_signal_items(data_context["market_items"]),
            "rate_model_items": html_list(data_context["model_notes"]),
            "api_source_items": api_source_items(data_context["source_notes"]),
        },
    )


def hub_page() -> str:
    cards = "\n".join(
        f"""<a class="insight-feature-card" href="{service_url(slug)}"><strong>{esc(guide['label'])}</strong><span>{esc(guide['range'])} planning range. Open state or city pages for localized versions.</span><em>Open guide</em></a>"""
        for slug, guide in SERVICE_GUIDES.items()
    )
    body = f"""
    <main id="main-content" class="insight-main">
      <section class="insight-hero" aria-labelledby="service-hub-title">
        <div>
          <div class="insight-breadcrumbs"><a href="/">Home</a> &rsaquo; Service Guides</div>
          <h1 id="service-hub-title">Service Guide Hub</h1>
          <p>Browse static high-intent contractor and project-cost guides. State and city pages link to generated local versions instead of relying on runtime-only pages.</p>
          <div class="insight-actions">
            <a href="#service-guides">Browse Guides</a>
            <a href="/service-guides/plumber/minnesota/">State Example</a>
            <a href="/service-guides/electrician/minnesota/lake-city/">City Example</a>
          </div>
        </div>
        <aside class="insight-panel" aria-label="Service guide generation summary">
          <h2>Static Generation</h2>
          <div class="insight-panel-grid">
            <div><strong>{len(SERVICE_GUIDES)}</strong><span>Services</span></div>
            <div><strong>50</strong><span>State sets</span></div>
            <div><strong>City</strong><span>Where pages exist</span></div>
            <div><strong>SEO</strong><span>Durable URLs</span></div>
          </div>
          <p class="insight-source">Generated pages can later be enriched with FRED, BEA, BLS, Census, and first-party quote data.</p>
        </aside>
      </section>
      <section class="insight-grid" id="service-guides" aria-label="Service guide categories">
        <article class="insight-card insight-wide">
          <h2>Contractor Service Guides</h2>
          <p>Open a national guide, then use state and city pages for location-specific versions.</p>
          <div class="insight-feature-grid" style="margin-top:12px">{cards}</div>
        </article>
      </section>
    </main>
"""
    return page_shell("Service Guide Hub", "Browse DataByArea high-intent contractor service guides with static state and city pages.", "/service-guides/", body)


def write_manifest(written: list[str]) -> None:
    manifest = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "services": sorted(SERVICE_GUIDES),
        "project_templates_per_service": {service: [item["slug"] for item in projects] for service, projects in PROJECT_GUIDES.items()},
        "page_count": len(written),
        "paths": written,
        "sample_paths": written[:20],
    }
    write(OUT_ROOT / "manifest.json", json.dumps(manifest, indent=2) + "\n")


def find_project(service_slug: str, project_slug: str) -> dict[str, Any]:
    for project in PROJECT_GUIDES.get(service_slug, []):
        if project["slug"] == project_slug:
            return project
    choices = ", ".join(project["slug"] for project in PROJECT_GUIDES.get(service_slug, []))
    raise SystemExit(f"Unknown project '{project_slug}' for service '{service_slug}'. Choices: {choices}")


def generation_candidates(args: argparse.Namespace) -> list[tuple[str, str, str, str]]:
    services = [args.service] if args.service else list(SERVICE_GUIDES)
    candidates: list[tuple[str, str, str, str]] = []
    city_routes = state_city_routes()
    city_lookup = {(state_slug, city_slug): (state_slug, state_name, city_slug) for state_slug, state_name, city_slug in city_routes}

    for service_slug in services:
        if service_slug not in SERVICE_GUIDES:
            raise SystemExit(f"Unknown service '{service_slug}'. Choices: {', '.join(SERVICE_GUIDES)}")
        projects = [find_project(service_slug, args.project)] if args.project else PROJECT_GUIDES.get(service_slug, [])
        for project in projects:
            if args.city:
                state_slug = args.state or "minnesota"
                state_name = US_STATES.get(state_slug, title_case_slug(state_slug))
                if (state_slug, args.city) in city_lookup:
                    _, state_name, city_slug = city_lookup[(state_slug, args.city)]
                else:
                    city_slug = args.city
                candidates.append((service_slug, state_slug, city_slug, project["slug"]))
            elif args.state:
                candidates.append((service_slug, args.state, "", project["slug"]))
            else:
                for state_slug in US_STATES:
                    candidates.append((service_slug, state_slug, "", project["slug"]))
                for state_slug, _state_name, city_slug in city_routes:
                    candidates.append((service_slug, state_slug, city_slug, project["slug"]))
    return candidates


def write_support_pages(service_slug: str, state_slug: str, city_slug: str, written: list[str]) -> tuple[dict[str, Any], str]:
    guide = SERVICE_GUIDES[service_slug]
    state_name = US_STATES.get(state_slug, title_case_slug(state_slug)) if state_slug else ""

    support_pages = [
        (OUT_ROOT / "index.html", "/service-guides/", hub_page()),
        (OUT_ROOT / service_slug / "index.html", service_url(service_slug), guide_page(service_slug, guide)),
    ]
    if state_slug:
        support_pages.append((OUT_ROOT / service_slug / state_slug / "index.html", service_url(service_slug, state_slug), guide_page(service_slug, guide, state_slug, state_name)))
    if state_slug and city_slug:
        support_pages.append((OUT_ROOT / service_slug / state_slug / city_slug / "index.html", service_url(service_slug, state_slug, city_slug), guide_page(service_slug, guide, state_slug, state_name, city_slug)))

    for path, url, content in support_pages:
        write(path, content)
        if url not in written:
            written.append(url)
    return guide, state_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate static high-intent service guide pages.")
    parser.add_argument("--limit", type=int, default=parse_int_env("DBA_SERVICE_GUIDE_LIMIT", 1), help="Maximum detailed project pages to generate. Defaults to 1.")
    parser.add_argument("--all", action="store_true", help="Generate every service/state/city/project combination. Use intentionally.")
    parser.add_argument("--service", default=os.getenv("DBA_SERVICE_GUIDE_SERVICE", "electrician"), help="Service slug to generate.")
    parser.add_argument("--project", default=os.getenv("DBA_SERVICE_GUIDE_PROJECT") or None, help="Project slug to generate. Defaults to the first project for the selected service.")
    parser.add_argument("--state", default=os.getenv("DBA_SERVICE_GUIDE_STATE", "minnesota"), help="State slug for the target guide.")
    parser.add_argument("--city", default=os.getenv("DBA_SERVICE_GUIDE_CITY", "lake-city"), help="City slug for the target guide. Leave empty for a state-level guide.")
    parser.add_argument("--clean", action="store_true", help="Clean service-guides output before generation.")
    parser.add_argument("--skip-api", action="store_true", help="Generate with template fallback data and source notes instead of calling public APIs.")
    parser.add_argument("--api-timeout", type=int, default=parse_int_env("DBA_SERVICE_GUIDE_API_TIMEOUT", 8), help="Timeout in seconds for each public API request.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned detailed guide URLs without writing files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    written: list[str] = []

    if args.all:
        args.limit = 0
        args.service = ""
        args.project = ""
        args.state = ""
        args.city = ""

    if args.clean and OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)

    candidates = generation_candidates(args)
    if args.limit > 0:
        candidates = candidates[: args.limit]

    planned_urls = [
        project_url(service_slug, project_slug, state_slug, city_slug)
        for service_slug, state_slug, city_slug, project_slug in candidates
    ]
    if args.dry_run:
        print("\n".join(planned_urls))
        return

    detail_count = 0
    for service_slug, state_slug, city_slug, project_slug in candidates:
        guide, state_name = write_support_pages(service_slug, state_slug, city_slug, written)
        project = find_project(service_slug, project_slug)
        path = OUT_ROOT / service_slug / state_slug
        if city_slug:
            path = path / city_slug
        path = path / project_slug / "index.html"
        write(
            path,
            project_page(
                service_slug,
                guide,
                project,
                state_slug,
                state_name,
                city_slug,
                use_api=not args.skip_api,
                api_timeout=args.api_timeout,
            ),
        )
        written.append(project_url(service_slug, project_slug, state_slug, city_slug))
        detail_count += 1

    write_manifest(written)
    print(f"Generated {detail_count} detailed service guide page(s), {len(written)} total support/static page(s)")
    print(f"Limit={args.limit or 'all'} API={'off' if args.skip_api else 'on'}")


if __name__ == "__main__":
    main()
