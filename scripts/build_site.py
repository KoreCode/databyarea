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
SITEMAPS_DIR = "sitemaps"
SITEMAP_SEGMENTS = ("states", "counties", "cities", "services")
ROBOTS_PATH = "robots.txt"
ALLOW_OVERWRITE = False
OUTPUT_ROOT = "."
MONETIZATION_FLAGS_PATH = "monetization_flags.json"
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
STATE_SLUGS = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
    "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
    "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new-hampshire", "new-jersey", "new-mexico",
    "new-york", "north-carolina", "north-dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode-island", "south-carolina", "south-dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west-virginia", "wisconsin", "wyoming", "district-of-columbia",
}

DEFAULT_MONETIZATION_FLAGS = {
    "global": {
        "affiliate_enabled": False,
        "lead_form_enabled": False,
        "quality_threshold_passed": False,
        "max_above_fold_units": 1,
    },
    "page_type": {
        "home_services": {"affiliate_enabled": True, "lead_form_enabled": False},
        "utilities": {"affiliate_enabled": False, "lead_form_enabled": False},
        "insurance": {"affiliate_enabled": False, "lead_form_enabled": False},
        "property_taxes": {"affiliate_enabled": False, "lead_form_enabled": False},
    },
    "geography": {
        "us": {"affiliate_enabled": True, "lead_form_enabled": False},
        "by_state": {"affiliate_enabled": True, "lead_form_enabled": False},
    },
    "sensitive_templates": {
        "enabled": False,
        "keywords": [
            "insurance",
            "tax",
            "medicare",
            "loan",
            "mortgage",
            "credit",
            "legal",
            "bankruptcy",
            "debt",
        ],
    },
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

def merge_dict(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged

def load_monetization_flags(path: str = MONETIZATION_FLAGS_PATH) -> dict:
    file_flags = load_json(path, {})
    if not isinstance(file_flags, dict):
        return DEFAULT_MONETIZATION_FLAGS
    return merge_dict(DEFAULT_MONETIZATION_FLAGS, file_flags)

def infer_page_type(slug: str, base: str) -> str:
    s = f"{slug} {base}".lower()
    if "insurance" in s:
        return "insurance"
    if "tax" in s:
        return "property_taxes"
    if "utility" in s or "energy" in s:
        return "utilities"
    return "home_services"

def infer_geography(slug: str) -> str:
    if "-by-state" in slug:
        return "by_state"
    return "us"

def is_sensitive_template(slug: str, base: str, flags: dict) -> bool:
    sensitive_cfg = flags.get("sensitive_templates", {})
    keywords = sensitive_cfg.get("keywords", [])
    haystack = f"{slug} {base}".lower()
    return any(str(keyword).lower() in haystack for keyword in keywords)

def get_monetization_settings(slug: str, base: str, flags: dict) -> dict:
    page_type = infer_page_type(slug, base)
    geography = infer_geography(slug)
    global_cfg = flags.get("global", {})

    settings = {
        "affiliate_enabled": bool(global_cfg.get("affiliate_enabled", False)),
        "lead_form_enabled": bool(global_cfg.get("lead_form_enabled", False)),
        "quality_threshold_passed": bool(global_cfg.get("quality_threshold_passed", False)),
        "max_above_fold_units": int(global_cfg.get("max_above_fold_units", 1)),
        "page_type": page_type,
        "geography": geography,
    }

    for scope in (
        flags.get("page_type", {}).get(page_type, {}),
        flags.get("geography", {}).get(geography, {}),
    ):
        if "affiliate_enabled" in scope:
            settings["affiliate_enabled"] = bool(scope["affiliate_enabled"])
        if "lead_form_enabled" in scope:
            settings["lead_form_enabled"] = bool(scope["lead_form_enabled"])
        if "max_above_fold_units" in scope:
            settings["max_above_fold_units"] = int(scope["max_above_fold_units"])

    if is_sensitive_template(slug, base, flags):
        sensitive_enabled = bool(flags.get("sensitive_templates", {}).get("enabled", False))
        if not settings["quality_threshold_passed"] or not sensitive_enabled:
            settings["affiliate_enabled"] = False
            settings["lead_form_enabled"] = False

    return settings

def build_affiliate_module(service_name: str, page_type: str, geography: str) -> str:
    return f"""
<section class="dba-monetization-module dba-affiliate-module" data-module="affiliate-recommendation" data-page-type="{page_type}" data-geography="{geography}">
  <h2>Recommended local quote options</h2>
  <p>
    <strong>Affiliate disclosure:</strong> We may earn a commission if you request quotes through partner links.
  </p>
  <ul>
    <li><a href="/contact/">Compare vetted {service_name.lower()} providers</a></li>
    <li><a href="/contact/">Request multiple quotes in one step</a></li>
  </ul>
</section>
""".strip()

def build_lead_form_module(service_name: str, page_type: str, geography: str) -> str:
    return f"""
<section class="dba-monetization-module dba-lead-form-module" data-module="lead-form" data-page-type="{page_type}" data-geography="{geography}">
  <h2>Need {service_name.lower()} quotes near you?</h2>
  <p>Share your project details and location to get matched with providers.</p>
  <form method="post" action="/contact/" class="dba-lead-form">
    <label for="zip">ZIP code</label><br>
    <input id="zip" name="zip" type="text" inputmode="numeric" pattern="[0-9]{5}" placeholder="e.g., 30309"><br><br>
    <label for="project">Project type</label><br>
    <input id="project" name="project" type="text" placeholder="e.g., panel upgrade"><br><br>
    <button type="submit">Get quote options</button>
  </form>
</section>
""".strip()

# =========================================================
# INTERNAL LINKING BUILDERS
# =========================================================
def build_related_links(current_slug: str, queue_slugs: list[str], published_map: dict) -> str:
    base, _intent = parse_slug(current_slug)
    cat = infer_category(base)

    candidates = []
    candidates.extend(CATEGORY_HUBS.get(cat, []))
    candidates.extend(GLOBAL_CORE)

    # Pull neighbors from queue for natural topical adjacency
    try:
        idx = queue_slugs.index(current_slug)
        neighbors = queue_slugs[max(0, idx - 12): idx] + queue_slugs[idx + 1: idx + 13]
        candidates.extend(neighbors)
    except ValueError:
        pass

    seen = set()
    chosen = []
    for c in candidates:
        c = c.strip("/")
        if not c or c == current_slug or c in seen:
            continue

        ok = (c in published_map) or (LINK_TO_QUEUED and c in queue_slugs)
        if not ok:
            continue

        seen.add(c)
        chosen.append(c)

    chosen = chosen[:6]
    if not chosen:
        return ""

    lis = "\n".join([f'  <li><a href="{href(s)}">{slug_to_title(s)}</a></li>' for s in chosen])
    return f"<ul>\n{lis}\n</ul>"

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
    monetization_flags = load_monetization_flags()
    monetization = get_monetization_settings(slug, base, monetization_flags)

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
    prev_next_html = build_prev_next(slug, queue_slugs, published_map)

    related_section = f"""
<h2>Related guides</h2>
{related_html}
""".strip() if related_html else ""

    keep_exploring_section = f"""
<h2>Keep exploring</h2>
{prev_next_html}
""".strip() if prev_next_html else ""

    today = datetime.utcnow().strftime("%Y-%m-%d")
    desc = f"Updated {today}. {service_name} {intent} with pricing factors, estimate tips, and FAQs."
    affiliate_block = (
        build_affiliate_module(service_name, monetization["page_type"], monetization["geography"])
        if monetization["affiliate_enabled"] else ""
    )
    lead_form_block = (
        build_lead_form_module(service_name, monetization["page_type"], monetization["geography"])
        if monetization["lead_form_enabled"] else ""
    )

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

{affiliate_block}

{faq_html}

{related_section}

{keep_exploring_section}

{lead_form_block}

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
    def classify_sitemap_segment(path: str) -> str:
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return "services"
        if parts[0] in {"state", "states"}:
            if len(parts) <= 2:
                return "states"
            if len(parts) == 3:
                return "counties"
            return "cities"
        if len(parts) >= 2 and parts[1] in STATE_SLUGS:
            if len(parts) == 2:
                return "states"
            if len(parts) == 3:
                return "counties"
            return "cities"
        return "services"

    def write_segment_sitemap(path: Path, pages: list[tuple[str, Path]]):
        urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for url_path, index_path in pages:
            u = ET.SubElement(urlset, "url")
            ET.SubElement(u, "loc").text = urljoin(SITE_URL.rstrip("/") + "/", url_path.lstrip("/"))
            ET.SubElement(u, "lastmod").text = datetime.utcfromtimestamp(
                index_path.stat().st_mtime
            ).strftime("%Y-%m-%d")
        ET.ElementTree(urlset).write(path, encoding="utf-8", xml_declaration=True)

    def validate_sitemap_integrity(segment_paths: list[Path]) -> None:
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        missing = []
        for xml_path in segment_paths:
            root = ET.parse(xml_path).getroot()
            for loc in root.findall("sm:url/sm:loc", ns):
                loc_text = (loc.text or "").strip()
                if not loc_text.startswith(SITE_URL):
                    continue
                rel_path = "/" + loc_text.replace(SITE_URL.rstrip("/"), "", 1).lstrip("/")
                file_path = Path("index.html") if rel_path == "/" else Path(rel_path.strip("/")) / "index.html"
                if not file_path.exists():
                    missing.append(rel_path)
        if missing:
            raise RuntimeError(
                "Sitemap integrity check failed. Missing index.html for: "
                + ", ".join(sorted(set(missing))[:20])
            )

    pages = sorted(set(iter_public_index_pages()), key=lambda item: item[0])
    segments: dict[str, list[tuple[str, Path]]] = {name: [] for name in SITEMAP_SEGMENTS}
    for url_path, index_path in pages:
        segments[classify_sitemap_segment(url_path)].append((url_path, index_path))

    os.makedirs(SITEMAPS_DIR, exist_ok=True)
    segment_paths: list[Path] = []
    newest_lastmod = datetime.utcnow().strftime("%Y-%m-%d")
    for name in SITEMAP_SEGMENTS:
        seg_path = Path(SITEMAPS_DIR) / f"{name}.xml"
        segment_paths.append(seg_path)
        write_segment_sitemap(seg_path, sorted(set(segments[name]), key=lambda item: item[0]))
        if segments[name]:
            newest_lastmod = max(
                newest_lastmod,
                max(datetime.utcfromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d") for _, p in segments[name]),
            )

    sitemapindex = ET.Element("sitemapindex", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for name in SITEMAP_SEGMENTS:
        sm = ET.SubElement(sitemapindex, "sitemap")
        ET.SubElement(sm, "loc").text = f"{SITE_URL.rstrip('/')}/{SITEMAPS_DIR}/{name}.xml"
        ET.SubElement(sm, "lastmod").text = newest_lastmod
    ET.ElementTree(sitemapindex).write(SITEMAP_PATH, encoding="utf-8", xml_declaration=True)

    validate_sitemap_integrity(segment_paths)

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
    remaining = [s for s in queue_slugs if s and s not in published][:daily_limit]

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
