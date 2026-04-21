import argparse
import os
import json
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

# =========================================================
# CONFIG (EDIT THESE IF NEEDED)
# =========================================================
SITE_URL = "https://databyarea.com"
DAILY_MAX = int(os.getenv("DBA_DAILY_MAX", "10"))
QUEUE_FILE = "data/core_pages.txt"
MANIFEST_PATH = "published_manifest.json"
SITEMAP_PATH = "sitemap.xml"
ROBOTS_PATH = "robots.txt"
ALLOW_OVERWRITE = False
OUTPUT_ROOT = "."
SITEMAP_EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "_deploy",
    "assets",
    "scripts",
    "site",
    "data",
    "logs",
    "node_modules",
}

# Ensure required legal pages exist (privacy-policy/terms)
ENSURE_SYSTEM_PAGES = True
OVERWRITE_SYSTEM_PAGES = False  # set True only if you want generator to replace your manual edits

# Internal linking safety:
# False = only link to pages that already exist (no 404 risk)
# True  = also link to queued pages (might 404 until published)
LINK_TO_QUEUED = False

# =========================================================
# SERVICE-SPECIFIC TONE
# =========================================================
SERVICE_TONES = {
    "electrician": {
        "drivers": [
            "licensing and continuing education requirements",
            "permit and inspection rules",
            "panel capacity and existing wiring condition",
            "access to walls, ceilings, and service panels",
        ],
        "jobs": [
            "outlet and switch replacements",
            "panel upgrades and breaker work",
            "lighting and fixture installation",
            "rewiring and circuit additions",
        ],
    },
    "plumber": {
        "drivers": [
            "emergency versus scheduled service",
            "pipe material and accessibility",
            "local plumbing codes",
            "fixture quality and replacement scope",
        ],
        "jobs": [
            "leak repairs and drain clearing",
            "fixture and faucet replacement",
            "water heater installation",
            "pipe replacement and rerouting",
        ],
    },
    "hvac": {
        "drivers": [
            "system size and efficiency rating",
            "existing ductwork condition",
            "local energy codes",
            "seasonal demand",
        ],
        "jobs": [
            "system replacement",
            "AC or furnace installation",
            "duct modifications",
            "maintenance and tune-ups",
        ],
    },
    "roof": {
        "drivers": [
            "roof pitch and complexity",
            "material type",
            "tear-off versus overlay",
            "local weather exposure",
        ],
        "jobs": [
            "shingle replacement",
            "leak repairs",
            "flashing and ventilation work",
            "full roof replacement",
        ],
    },
    "concrete": {
        "drivers": [
            "site preparation and grading",
            "reinforcement requirements",
            "weather and curing conditions",
            "equipment access",
        ],
        "jobs": [
            "driveways and slabs",
            "patios and walkways",
            "footings and foundations",
            "removal and replacement",
        ],
    },
    "general": {
        "drivers": [
            "labor availability",
            "permit requirements",
            "material access",
            "job complexity",
        ],
        "jobs": [
            "repairs",
            "installations",
            "upgrades",
            "full replacements",
        ],
    },
}

# =========================================================
# INTERNAL LINKING HUBS (EDIT ANYTIME)
# =========================================================
CATEGORY_HUBS = {
    "electrician": [
        "electrician-rates-by-state",
        "ev-charger-installation-cost-by-state",
        "electrical-panel-upgrade-cost-by-state",
        "whole-house-rewiring-cost-by-state",
        "ceiling-fan-installation-cost-by-state",
    ],
    "plumber": [
        "plumber-rates-by-state",
        "water-heater-installation-cost-by-state",
        "tankless-water-heater-installation-cost-by-state",
        "drain-cleaning-cost-by-state",
        "sewer-line-repair-cost-by-state",
    ],
    "hvac": [
        "hvac-installation-cost-by-state",
        "ac-installation-cost-by-state",
        "ac-repair-cost-by-state",
        "furnace-installation-cost-by-state",
        "ductwork-installation-cost-by-state",
    ],
    "roof": [
        "roof-replacement-cost-by-state",
        "roof-repair-cost-by-state",
        "metal-roof-installation-cost-by-state",
        "gutter-installation-cost-by-state",
        "gutter-guard-installation-cost-by-state",
    ],
    "concrete": [
        "concrete-driveway-cost-by-state",
        "concrete-patio-cost-by-state",
        "concrete-walkway-cost-by-state",
        "foundation-repair-cost-by-state",
        "retaining-wall-installation-cost-by-state",
    ],
    "general": [
        "window-replacement-cost-by-state",
        "door-installation-cost-by-state",
        "insulation-installation-cost-by-state",
        "garage-door-repair-cost-by-state",
        "deck-building-cost-by-state",
    ],
}

GLOBAL_CORE = [
    "electrician-rates-by-state",
    "plumber-rates-by-state",
    "hvac-installation-cost-by-state",
    "roof-replacement-cost-by-state",
    "foundation-repair-cost-by-state",
]

GEO_SIBLING_CATEGORIES = (
    "utility-costs",
    "cost-of-living",
    "property-taxes",
    "insurance-costs",
)

HIGH_DEMAND_MARKETS = (
    "california",
    "texas",
    "florida",
    "new-york",
    "illinois",
    "washington",
)

# =========================================================
# BASIC HELPERS
# =========================================================
def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def read_lines(path: str):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip().strip("/") for l in f if l.strip() and not l.startswith("#")]

def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def seeded_rng(slug: str) -> random.Random:
    seed = sum((i + 1) * ord(c) for i, c in enumerate(slug))
    return random.Random(seed)

def slug_to_title(slug: str) -> str:
    return slug.strip("/").replace("-", " ").title()

def href(slug: str) -> str:
    return f"/{slug.strip('/')}/"

def parse_geo_slug(slug: str) -> tuple[str | None, str | None, str | None]:
    parts = [p for p in slug.strip("/").split("/") if p]
    if len(parts) < 2:
        return None, None, None
    category = parts[0]
    if category not in GEO_SIBLING_CATEGORIES:
        return None, None, None
    state = parts[1]
    city_or_county = parts[2] if len(parts) >= 3 else None
    return category, state, city_or_county

def has_slug(slug: str, queue_slugs: list[str], published_map: dict) -> bool:
    return (slug in published_map) or (LINK_TO_QUEUED and slug in queue_slugs)

def slug_label(slug: str) -> str:
    parts = [p for p in slug.strip("/").split("/") if p]
    if not parts:
        return "DataByArea"
    if len(parts) == 1:
        return slug_to_title(parts[0])

    if parts[0] in GEO_SIBLING_CATEGORIES:
        category_name = slug_to_title(parts[0])
        state_name = slug_to_title(parts[1])
        if len(parts) == 2:
            return f"{category_name} in {state_name}"
        return f"{category_name} in {slug_to_title(parts[2])}, {state_name}"

    return slug_to_title(parts[-1])

# =========================================================
# SYSTEM PAGES (PRIVACY / TERMS)
# =========================================================
def write_if_missing(path: str, content: str, overwrite: bool = False) -> bool:
    """Write file if missing. Returns True if written/overwritten, False otherwise."""
    folder = os.path.dirname(path)
    if folder:
        ensure_dir(folder)
    if os.path.exists(path) and not overwrite:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True

def privacy_policy_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Privacy Policy | DataByArea</title>
  <meta name="description" content="Privacy policy for DataByArea explaining how information is collected, used, and protected.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

<header>
  <p><a href="/">DataByArea</a></p>
</header>

<main>
  <h1>Privacy Policy</h1>

  <p>
    At DataByArea, we respect your privacy. This page explains what information we collect,
    how it is used, and the choices you have regarding your data.
  </p>

  <h2>Information We Collect</h2>
  <p>
    DataByArea does not collect personally identifiable information such as names,
    addresses, or payment details.
  </p>
  <p>
    Like most websites, we may collect limited, non-personal information automatically,
    including browser type, device type, approximate location, and pages visited.
    This data is used only to improve site performance and content relevance.
  </p>

  <h2>Cookies</h2>
  <p>
    We may use cookies or similar technologies to understand how visitors interact
    with the site. Cookies do not identify you personally and can be disabled in your browser
    settings at any time.
  </p>

  <h2>Third-Party Services</h2>
  <p>
    DataByArea may use third-party analytics or advertising services that collect
    anonymous usage data in accordance with their own privacy policies.
  </p>

  <h2>External Links</h2>
  <p>
    Our site may contain links to external websites. We are not responsible for the
    content or privacy practices of those sites.
  </p>

  <h2>Changes to This Policy</h2>
  <p>
    This privacy policy may be updated from time to time. Any changes will be posted
    on this page with an updated effective date.
  </p>

  <h2>Contact</h2>
  <p>
    If you have questions about this privacy policy, please contact us through the
    information provided on our contact page.
  </p>

  <p><em>Last updated: February 2026</em></p>
</main>

</body>
</html>
"""

def terms_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Terms of Use | DataByArea</title>
  <meta name="description" content="Terms of use for DataByArea outlining content usage, disclaimers, and limitations.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

<header>
  <p><a href="/">DataByArea</a></p>
</header>

<main>
  <h1>Terms of Use</h1>

  <p>
    By accessing and using DataByArea, you agree to the terms on this page. If you do not agree,
    please do not use the site.
  </p>

  <h2>Information Only (Not Professional Advice)</h2>
  <p>
    DataByArea provides general information about costs, rates, and pricing factors.
    Content is provided for informational purposes only and may not reflect current pricing
    in your specific location. Always confirm details with qualified professionals and local authorities.
  </p>

  <h2>No Guarantees</h2>
  <p>
    We work to keep content accurate and helpful, but we do not guarantee completeness, accuracy,
    or suitability for any specific purpose. Use the site at your own discretion.
  </p>

  <h2>External Links</h2>
  <p>
    The site may link to external websites. We are not responsible for the content, policies,
    or practices of third-party sites.
  </p>

  <h2>Limitation of Liability</h2>
  <p>
    To the maximum extent permitted by law, DataByArea is not liable for any losses or damages
    arising from the use of this site.
  </p>

  <h2>Updates to These Terms</h2>
  <p>
    These terms may be updated from time to time. Changes will be posted on this page.
  </p>

  <p><em>Last updated: February 2026</em></p>
</main>

</body>
</html>
"""

def ensure_system_pages(manifest: dict) -> None:
    """Ensure privacy-policy/terms exist and appear in manifest + sitemap."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    published = manifest.setdefault("published", {})

    system = {
        "privacy-policy": privacy_policy_html(),
        "terms": terms_html(),
    }

    for slug, html in system.items():
        folder = os.path.join(OUTPUT_ROOT, slug)
        index_path = os.path.join(folder, "index.html")
        ensure_dir(folder)

        wrote = write_if_missing(index_path, html, overwrite=OVERWRITE_SYSTEM_PAGES)

        # Ensure in manifest for sitemap even if file already existed
        if slug not in published:
            published[slug] = {"published_at": today, "system": True}
        else:
            # Don't change existing date unless we actually overwrote content
            if wrote:
                published[slug]["published_at"] = today
                published[slug]["system"] = True

# =========================================================
# SLUG PARSING + CATEGORY
# =========================================================
def parse_slug(slug: str):
    s = slug.replace("-by-state", "").replace("-", " ")
    intent = "by state"

    if "cost" in s:
        s = s.replace(" cost", "")
        intent = "cost by state"
    if "rates" in s:
        s = s.replace(" rates", "")
        intent = "rates by state"

    return s.strip(), intent

def infer_category(base: str) -> str:
    b = base.lower()

    # direct keys
    for k in SERVICE_TONES.keys():
        if k != "general" and k in b:
            return k

    # heuristics
    if "roof" in b or "gutter" in b:
        return "roof"
    if "concrete" in b or "foundation" in b or "masonry" in b or "retaining wall" in b:
        return "concrete"
    if "hvac" in b or "furnace" in b or b.startswith("ac") or " ac " in f" {b} " or "duct" in b:
        return "hvac"
    if "plumb" in b or "water heater" in b or "drain" in b or "sewer" in b or "septic" in b:
        return "plumber"
    if "electric" in b or "panel" in b or "rewir" in b or "ev charger" in b:
        return "electrician"

    return "general"

def money_range(rng: random.Random):
    low = rng.choice([65, 70, 75, 80, 85, 90])
    high = rng.choice([120, 135, 150, 165])
    avg = int((low + high) / 2)
    return low, high, avg

# =========================================================
# INTERNAL LINKING BUILDERS
# =========================================================
def build_related_links(current_slug: str, queue_slugs: list[str], published_map: dict) -> str:
    base, _intent = parse_slug(current_slug)
    cat = infer_category(base)

    candidates: list[tuple[str, str]] = []
    candidates.extend([(slug, "core-topic") for slug in CATEGORY_HUBS.get(cat, [])])
    candidates.extend([(slug, "global-core") for slug in GLOBAL_CORE])

    geo_category, geo_state, geo_place = parse_geo_slug(current_slug)
    if geo_category and geo_state:
        # Parent geography: city/county pages should point to state-level parent page.
        if geo_place:
            parent_slug = f"{geo_category}/{geo_state}"
            candidates.append((parent_slug, "parent-geography"))

        # Same geography, sibling categories (utility <-> COL <-> taxes <-> insurance).
        geo_suffix = f"{geo_state}/{geo_place}" if geo_place else geo_state
        for sibling_category in GEO_SIBLING_CATEGORIES:
            sibling_slug = f"{sibling_category}/{geo_suffix}"
            if sibling_slug != current_slug:
                candidates.append((sibling_slug, "sibling-category"))

        # Nearby/peer geographies: same state peers for city/county pages, top markets for state pages.
        if geo_place:
            for q_slug in queue_slugs:
                q_category, q_state, q_place = parse_geo_slug(q_slug)
                if (
                    q_slug != current_slug
                    and q_category == geo_category
                    and q_state == geo_state
                    and q_place
                ):
                    candidates.append((q_slug, "peer-geography"))
        else:
            for market_state in HIGH_DEMAND_MARKETS:
                if market_state != geo_state:
                    candidates.append((f"{geo_category}/{market_state}", "peer-geography"))

    # Pull neighbors from queue for natural topical adjacency
    try:
        idx = queue_slugs.index(current_slug)
        neighbors = queue_slugs[max(0, idx - 12): idx] + queue_slugs[idx + 1: idx + 13]
        candidates.extend([(slug, "queue-neighbor") for slug in neighbors])
    except ValueError:
        pass

    seen = set()
    chosen: list[tuple[str, str]] = []
    for c, relation in candidates:
        c = c.strip("/")
        if not c or c == current_slug or c in seen:
            continue

        ok = has_slug(c, queue_slugs, published_map)
        if not ok:
            continue

        seen.add(c)
        chosen.append((c, relation))

    chosen = chosen[:6]
    if not chosen:
        return ""

    def anchor_text(slug: str, relation: str) -> str:
        label = slug_label(slug)
        if relation == "parent-geography":
            return f"Statewide overview: {label}"
        if relation == "sibling-category":
            return f"Compare with {label}"
        if relation == "peer-geography":
            return f"Peer market snapshot: {label}"
        if relation == "core-topic":
            return f"Related service guide: {label}"
        if relation == "global-core":
            return f"Most-read national guide: {label}"
        return f"Continue researching: {label}"

    lis = "\n".join(
        [f'  <li><a href="{href(slug)}">{anchor_text(slug, relation)}</a></li>' for slug, relation in chosen]
    )
    return f"<ul>\n{lis}\n</ul>"

def build_compare_module(current_slug: str, queue_slugs: list[str], published_map: dict) -> str:
    geo_category, geo_state, geo_place = parse_geo_slug(current_slug)
    if not geo_category or not geo_state:
        return ""

    if geo_place:
        heading = f"Compare {slug_to_title(geo_place)}, {slug_to_title(geo_state)}"
        sibling_suffix = f"{geo_state}/{geo_place}"
    else:
        heading = f"Compare {slug_to_title(geo_state)} with other markets"
        sibling_suffix = geo_state

    links: list[tuple[str, str]] = []
    for sibling_category in GEO_SIBLING_CATEGORIES:
        sibling_slug = f"{sibling_category}/{sibling_suffix}"
        if sibling_slug != current_slug and has_slug(sibling_slug, queue_slugs, published_map):
            links.append((sibling_slug, f"Compare against {slug_label(sibling_slug)}"))

    if geo_place:
        peer_prefix = f"{geo_category}/{geo_state}/"
        peers = [
            s for s in queue_slugs
            if s.startswith(peer_prefix) and s != current_slug and has_slug(s, queue_slugs, published_map)
        ][:3]
        links.extend([(slug, f"Nearby benchmark: {slug_label(slug)}") for slug in peers])
    else:
        for market in HIGH_DEMAND_MARKETS:
            if market == geo_state:
                continue
            peer_slug = f"{geo_category}/{market}"
            if has_slug(peer_slug, queue_slugs, published_map):
                links.append((peer_slug, f"State-to-state comparison: {slug_label(peer_slug)}"))
            if len(links) >= 8:
                break

    if not links:
        return ""

    list_html = "\n".join([f'  <li><a href="{href(slug)}">{label}</a></li>' for slug, label in links[:8]])
    return f"""
<section aria-label="Comparison links">
<h2>{heading}</h2>
<p>Use these comparison pages to evaluate costs and taxes across related places before requesting quotes.</p>
<ul>
{list_html}
</ul>
</section>
""".strip()

def reorder_queue_for_clusters(remaining_slugs: list[str], published_map: dict) -> list[str]:
    remaining_set = set(remaining_slugs)

    def cluster_size(state: str) -> int:
        return sum(
            1
            for category in GEO_SIBLING_CATEGORIES
            if f"{category}/{state}" in remaining_set or f"{category}/{state}" in published_map
        )

    def sort_key(slug: str) -> tuple[int, int, int, int, str]:
        category, state, place = parse_geo_slug(slug)
        if not category or not state:
            return (2, 2, 0, 0, slug)

        demand_rank = HIGH_DEMAND_MARKETS.index(state) if state in HIGH_DEMAND_MARKETS else len(HIGH_DEMAND_MARKETS)
        # Keep state + city/county pages for the same market tightly grouped.
        level_rank = 0 if place is None else 1
        completeness_rank = -cluster_size(state)
        return (0, demand_rank, level_rank, completeness_rank, slug)

    return sorted(remaining_slugs, key=sort_key)

def build_prev_next(current_slug: str, queue_slugs: list[str], published_map: dict) -> str:
    # only published pages to avoid broken links
    published_in_order = [s for s in queue_slugs if s in published_map]
    if current_slug not in published_map:
        return ""

    try:
        i = published_in_order.index(current_slug)
    except ValueError:
        return ""

    prev_slug = published_in_order[i - 1] if i > 0 else None
    next_slug = published_in_order[i + 1] if i < len(published_in_order) - 1 else None

    parts = []
    if prev_slug:
        parts.append(f'<a href="{href(prev_slug)}">← {slug_to_title(prev_slug)}</a>')
    if next_slug:
        parts.append(f'<a href="{href(next_slug)}">{slug_to_title(next_slug)} →</a>')

    if not parts:
        return ""
    return "<p>" + " &nbsp; | &nbsp; ".join(parts) + "</p>"

# =========================================================
# PAGE BUILDER (HUMAN-STYLE + LINKS)
# =========================================================
def build_page(slug: str, queue_slugs: list[str], published_map: dict) -> str:
    rng = seeded_rng(slug)
    base, intent = parse_slug(slug)
    service_name = base.title()
    year = datetime.utcnow().strftime("%Y")

    tone_key = infer_category(base)
    tone = SERVICE_TONES.get(tone_key, SERVICE_TONES["general"])

    low, high, avg = money_range(rng)

    intro = rng.choice([
        f"Pricing for {base} work can vary more than most homeowners expect, especially when state rules and labor markets differ.",
        f"{service_name} costs aren’t universal — location, scope, and code requirements all influence the final number.",
        f"When comparing {base} quotes, state-level differences are often the biggest factor."
    ])

    pricing = rng.choice([
        f"Across many states, labor commonly falls in the <strong>${low}–${high}/hour</strong> range, with a typical midpoint around <strong>${avg}</strong>.",
        f"A reasonable national labor ballpark is <strong>${low}–${high} per hour</strong>, before permits and materials.",
        f"Many projects land near <strong>${low}–${high}/hr</strong> for labor, depending on local requirements."
    ])

    drivers_html = "".join(f"<li>{d.capitalize()}</li>" for d in tone["drivers"])
    jobs_html = "".join(f"<li>{j.capitalize()}</li>" for j in tone["jobs"])

    faq_html = f"""
<h2>FAQ</h2>

<h3>Why does {base} pricing change by state?</h3>
<p>Labor licensing, permit rules, inspection requirements, and local demand all affect final pricing.</p>

<h3>Is hourly or flat-rate pricing better?</h3>
<p>Hourly pricing works well for uncertain repairs, while flat-rate bids are usually better for clearly defined projects.</p>

<h3>How can I avoid surprise charges?</h3>
<p>Get the scope in writing, ask what triggers add-ons, and confirm permits and cleanup are included.</p>
"""

    related_html = build_related_links(slug, queue_slugs, published_map)
    compare_html = build_compare_module(slug, queue_slugs, published_map)
    prev_next_html = build_prev_next(slug, queue_slugs, published_map)

    related_section = f"""
<h2>Related guides</h2>
{related_html}
""".strip() if related_html else ""

    keep_exploring_section = f"""
<h2>Keep exploring</h2>
{prev_next_html}
""".strip() if prev_next_html else ""

    compare_section = compare_html if compare_html else ""

    today = datetime.utcnow().strftime("%Y-%m-%d")
    desc = f"Updated {today}. {service_name} {intent} with pricing factors, estimate tips, and FAQs."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{service_name} {intent.title()} ({year} Guide)</title>
<meta name="description" content="{desc}">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>

<header>
  <p><a href="/">DataByArea</a></p>
</header>

<main>
<h1>{service_name} {intent.title()}</h1>

<p>{intro}</p>
<p>{pricing}</p>

<h2>What affects {service_name.lower()} pricing?</h2>
<ul>
{drivers_html}
</ul>

<h2>Common {service_name.lower()} projects</h2>
<ul>
{jobs_html}
</ul>

<h2>How to compare quotes</h2>
<ul>
  <li>Get at least two written estimates</li>
  <li>Confirm the same scope is being priced</li>
  <li>Ask about permits, inspections, and warranties</li>
  <li>Clarify what causes additional charges</li>
</ul>

{faq_html}

{compare_section}

{related_section}

{keep_exploring_section}

<p><strong>Last updated:</strong> {today}</p>
</main>

<footer style="margin-top:40px;font-size:14px;">
<p><a href="/privacy-policy/">Privacy</a> • <a href="/terms/">Terms</a></p>
</footer>

</body>
</html>
"""

# =========================================================
# SITEMAP + ROBOTS
 # SITEMAP + ROBOTS
# =========================================================
def iter_public_index_pages():
    """
    Yield tuples of (url_path, index_file_path) for public-facing index pages.
    """
    for root, dirs, files in os.walk(OUTPUT_ROOT):
        rel_root = os.path.relpath(root, OUTPUT_ROOT)
        if rel_root == ".":
            rel_root = ""

        # Prune non-public folders from crawl.
        dirs[:] = [
            d for d in dirs
            if d not in SITEMAP_EXCLUDE_DIRS and not d.startswith(".")
        ]

        if "index.html" not in files:
            continue

        index_path = Path(root) / "index.html"
        if rel_root:
            url_path = "/" + rel_root.replace(os.sep, "/").strip("/") + "/"
        else:
            url_path = "/"
        yield url_path, index_path

def update_sitemap(manifest: dict):
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    pages = sorted(set(iter_public_index_pages()), key=lambda item: item[0])

    for url_path, index_path in pages:
        u = ET.SubElement(urlset, "url")
        ET.SubElement(u, "loc").text = urljoin(SITE_URL.rstrip("/") + "/", url_path.lstrip("/"))
        ET.SubElement(u, "lastmod").text = datetime.utcfromtimestamp(
            index_path.stat().st_mtime
        ).strftime("%Y-%m-%d")

    ET.ElementTree(urlset).write(SITEMAP_PATH, encoding="utf-8", xml_declaration=True)

def update_robots():
    with open(ROBOTS_PATH, "w", encoding="utf-8") as f:
        f.write(
            "User-agent: *\n"
            "Allow: /\n\n"
            f"Sitemap: {SITE_URL.rstrip('/')}/{SITEMAP_PATH}\n"
        )

# =========================================================
# MAIN
# =========================================================
def main(daily_max: int | None = None):
    queue_slugs = read_lines(QUEUE_FILE)

    # If queue file doesn't exist yet, generate nothing accidentally
    if not queue_slugs:
        print(f"No queue found at {QUEUE_FILE}. Add slugs (one per line) and re-run.")
        manifest = load_json(MANIFEST_PATH, {"published": {}, "history": []})
        if ENSURE_SYSTEM_PAGES:
            ensure_system_pages(manifest)
            save_json(MANIFEST_PATH, manifest)
        update_sitemap(manifest)
        update_robots()
        return

    manifest = load_json(MANIFEST_PATH, {"published": {}, "history": []})

    if ENSURE_SYSTEM_PAGES:
        ensure_system_pages(manifest)

    published = manifest.get("published", {})

    daily_limit = daily_max if daily_max is not None else DAILY_MAX
    # Only publish new slugs, limited by daily_limit
    unpublished = [s for s in queue_slugs if s and s not in published]
    prioritized_unpublished = reorder_queue_for_clusters(unpublished, published)
    remaining = prioritized_unpublished[:daily_limit]

    if not remaining:
        save_json(MANIFEST_PATH, manifest)
        update_sitemap(manifest)
        update_robots()
        print("Nothing new to publish.")
        return

    count = 0
    skipped_existing_file = 0

    for slug in remaining:
        folder = os.path.join(OUTPUT_ROOT, slug)
        index_path = os.path.join(folder, "index.html")
        ensure_dir(folder)

        # Create HTML (uses internal links based on what's already published)
        html = build_page(slug, queue_slugs, published)

        if os.path.exists(index_path) and not ALLOW_OVERWRITE:
            # Don't overwrite, but mark published so it doesn't re-queue forever
            skipped_existing_file += 1
            published[slug] = {"published_at": datetime.utcnow().strftime("%Y-%m-%d")}
            continue

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)

        published[slug] = {"published_at": datetime.utcnow().strftime("%Y-%m-%d")}
        count += 1

    manifest["published"] = published
    manifest.setdefault("history", []).append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "attempted": len(remaining),
        "written": count,
        "skipped_existing_file": skipped_existing_file,
        "daily_max": daily_limit,
        "link_to_queued": LINK_TO_QUEUED
    })

    save_json(MANIFEST_PATH, manifest)
    update_sitemap(manifest)
    update_robots()

    print(f"Published {count} pages. (Skipped existing index.html: {skipped_existing_file})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build/publish site pages from queued slugs.")
    parser.add_argument("--daily-max", type=int, default=None, help="Maximum number of new service slugs to publish this run.")
    args = parser.parse_args()
    main(daily_max=args.daily_max)
