# publish_popular_cities_daily.py
# Publishes a safe number of *popular city* pages each day based on data/popular_cities.csv.
#
# What it does:
# - Reads data/popular_cities.csv (columns: state, city)
# - Creates city pages under each section:
#     /cost-of-living/<state>/<city-slug>/index.html
#     /utility-costs/<state>/<city-slug>/index.html
#     /property-taxes/<state>/<city-slug>/index.html
#     /insurance-costs/<state>/<city-slug>/index.html
# - Publishes up to DAILY_CITY_MAX new city pages total per run
# - Never overwrites existing city pages unless --overwrite
# - Injects a "Major cities" block into state index pages by default (disable with --no-inject)
# - Updates .daily_city_runs.json so you don't accidentally run twice in a day (UTC)
#
# Usage:
#   python publish_popular_cities_daily.py
#   python publish_popular_cities_daily.py --max 20
#   python publish_popular_cities_daily.py --inject
#   python publish_popular_cities_daily.py --inject --max 20
#   python publish_popular_cities_daily.py --no-inject
#   python publish_popular_cities_daily.py --force
#
# Tip: run this BEFORE make-site.py, then run make-site.py to rebuild sitemap/robots.

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SITE_NAME = "DataByArea"
SITE_URL = "https://databyarea.com"
CSS_PATH = "/assets/styles.css"

POPULAR_CSV = Path("data/popular_cities.csv")
POPULAR_CSV_FALLBACK = Path("popular_cities.csv")
RUN_LOG = Path(".daily_city_runs.json")

SECTIONS = [
    "cost-of-living",
    "utility-costs",
    "property-taxes",
    "insurance-costs",
]

US_STATES = {
    "alabama":"Alabama","alaska":"Alaska","arizona":"Arizona","arkansas":"Arkansas","california":"California",
    "colorado":"Colorado","connecticut":"Connecticut","delaware":"Delaware","florida":"Florida","georgia":"Georgia",
    "hawaii":"Hawaii","idaho":"Idaho","illinois":"Illinois","indiana":"Indiana","iowa":"Iowa","kansas":"Kansas",
    "kentucky":"Kentucky","louisiana":"Louisiana","maine":"Maine","maryland":"Maryland","massachusetts":"Massachusetts",
    "michigan":"Michigan","minnesota":"Minnesota","mississippi":"Mississippi","missouri":"Missouri","montana":"Montana",
    "nebraska":"Nebraska","nevada":"Nevada","new-hampshire":"New Hampshire","new-jersey":"New Jersey","new-mexico":"New Mexico",
    "new-york":"New York","north-carolina":"North Carolina","north-dakota":"North Dakota","ohio":"Ohio","oklahoma":"Oklahoma",
    "oregon":"Oregon","pennsylvania":"Pennsylvania","rhode-island":"Rhode Island","south-carolina":"South Carolina",
    "south-dakota":"South Dakota","tennessee":"Tennessee","texas":"Texas","utah":"Utah","vermont":"Vermont",
    "virginia":"Virginia","washington":"Washington","west-virginia":"West Virginia","wisconsin":"Wisconsin","wyoming":"Wyoming",
}

SECTION_META = {
    "cost-of-living": {
        "title": "Cost of Living",
        "summary": "housing, groceries, utilities, healthcare, and transportation",
    },
    "utility-costs": {
        "title": "Utility Costs",
        "summary": "electricity, natural gas, water, sewer, and internet costs",
    },
    "property-taxes": {
        "title": "Property Tax Rates",
        "summary": "effective property tax rates and homeowner tax burden",
    },
    "insurance-costs": {
        "title": "Insurance Costs",
        "summary": "auto, home, renters, and health insurance benchmarks",
    },
}

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = s.replace(".", "")
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s

def utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def already_ran_today(log: dict) -> bool:
    return log.get("last_run_utc") == utc_date_str()

def read_popular_list() -> list[tuple[str,str]]:
    csv_path = POPULAR_CSV if POPULAR_CSV.exists() else POPULAR_CSV_FALLBACK
    if not csv_path.exists():
        raise SystemExit(f"Missing {POPULAR_CSV} (or fallback {POPULAR_CSV_FALLBACK}). Put a CSV with columns: state,city")
    out = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit("popular_cities.csv has no header row.")
        fields = [c.strip().lower() for c in reader.fieldnames]
        if "state" not in fields or "city" not in fields:
            raise SystemExit(f"popular_cities.csv must have columns state,city. Found: {reader.fieldnames}")
        s_col = reader.fieldnames[fields.index("state")]
        c_col = reader.fieldnames[fields.index("city")]
        for row in reader:
            st = slugify((row.get(s_col) or "").strip())
            city = (row.get(c_col) or "").strip()
            if not st or not city:
                continue
            if st not in US_STATES:
                # skip anything not in your current state folder structure
                continue
            out.append((st, city))
    # de-dup preserve order
    seen = set()
    final = []
    for st, city in out:
        key = (st, city.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        final.append((st, city))
    return final

def city_page_html(section: str, state_slug: str, city_name: str) -> str:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    state_name = US_STATES.get(state_slug, state_slug.replace("-", " ").title())
    city_slug = slugify(city_name)

    title = f"{city_name} {state_name} {section.replace('-', ' ').title()} | {SITE_NAME}"
    desc = f"Local comparisons for {city_name}, {state_name} in {section.replace('-', ' ')}. Updated regularly."
    canonical = f"{SITE_URL}/{section}/{state_slug}/{city_slug}/"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="{canonical}">
  <link rel="stylesheet" href="{CSS_PATH}">
</head>
<body>
  <div class="container">
    <h1>{city_name}, {state_name}</h1>
    <p class="lede">{section.replace('-', ' ').title()} snapshot and links for {city_name}, {state_name}.</p>

    <h2>Explore</h2>
    <ul class="gridList">
      <li><a href="/{section}/{state_slug}/">{section.replace('-', ' ').title()} in {state_name}</a></li>
      <li><a href="/{section}/">{section.replace('-', ' ').title()} by State</a></li>
      <li><a href="/services/">Service Cost Guides</a></li>
    </ul>

    <p><em>Last updated: {today}</em></p>
  </div>
</body>
</html>
"""

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def ensure_state_index(section: str, state_slug: str):
    folder = Path(section) / state_slug
    ensure_dir(folder)
    idx = folder / "index.html"
    if idx.exists():
        return
    state_name = US_STATES[state_slug]
    section_meta = SECTION_META[section]
    today = datetime.utcnow().strftime("%Y-%m-%d")
    section_title = section_meta["title"]
    title = f"{section_title} in {state_name} | {SITE_NAME}"
    desc = (
        f"Explore {section_title.lower()} in {state_name}. "
        f"Compare state averages and city-level differences."
    )
    canonical = f"{SITE_URL}/{section}/{state_slug}/"
    related_links = []
    for other_section in SECTIONS:
        if other_section == section:
            continue
        other_title = SECTION_META[other_section]["title"]
        related_links.append(
            f'<li><a href="/{other_section}/{state_slug}/">{other_title} in {state_name}</a></li>'
        )
    related_html = "\n          ".join(related_links)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="{canonical}">
  <link rel="stylesheet" href="{CSS_PATH}">
</head>
<body>
  <div class="container">
    <div class="nav">
      <div class="brand">
        <img src="/assets/logo.png" alt="Data By Area logo" class="logo">
        <div class="brand-text">
          <strong>Data By Area</strong>
          <span>Costs • Rates • Public Data</span>
        </div>
      </div>
      <div class="navlinks">
        <a class="pill" href="/">Home</a>
        <a class="pill" href="/cost-of-living/">Cost of Living</a>
        <a class="pill" href="/utility-costs/">Utility Costs</a>
        <a class="pill" href="/property-taxes/">Property Tax Rates</a>
        <a class="pill" href="/insurance-costs/">Insurance Costs</a>
      </div>
    </div>

    <div class="hero">
      <h1>{section_title} in {state_name}</h1>
      <p>{desc}</p>
      <div class="breadcrumbs">
        <a href="/">Home</a> › <a href="/{section}/">{section_title}</a> › <span>{state_name}</span>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>What you can compare</h2>
        <p>Use this page to review {section_meta["summary"]} across {state_name}.</p>
        <ul class="list">
          <li class="item">Statewide averages and regional variation</li>
          <li class="item">City-level snapshots for major metros</li>
          <li class="item">Cross-category links for fuller context</li>
        </ul>
      </div>

      <div class="card">
        <h2>Related {state_name} pages</h2>
        <p>Explore other cost categories for {state_name}.</p>
        <ul class="list">
          {related_html}
        </ul>
        <a class="btn" href="/{section}/">Back to {section_title} states</a>
      </div>
    </div>

    <!-- POPULAR_CITIES:ANCHOR -->

    <div class="footer">
      <p><strong>Disclaimer:</strong> Informational estimates only. Costs and rates vary by household, provider, and local area.</p>
      <p><a href="/about/">About</a> · <a href="/privacy/">Privacy Policy</a> · <a href="/contact/">Contact</a></p>
      <p>Last updated: {today}</p>
    </div>
  </div>
  <script defer src="/assets/version-footer.js"></script>
</body>
</html>
"""
    idx.write_text(html, encoding="utf-8")

def inject_city_block(section: str, state_slug: str, city_pairs: list[tuple[str,str]], max_links: int = 24) -> bool:
    idx = Path(section) / state_slug / "index.html"
    if not idx.exists():
        return False
    html = idx.read_text(encoding="utf-8", errors="ignore")
    if "<!-- POPULAR_CITIES:START -->" in html:
        return False

    state_name = US_STATES[state_slug]
    # pick cities for this state in the same order as the popular list
    cities = [c for st, c in city_pairs if st == state_slug][:max_links]
    if not cities:
        return False

    lis = "\n".join(
        f'<li><a href="/{section}/{state_slug}/{slugify(c)}/">{c}</a></li>' for c in cities
    )

    block = f"""<!-- POPULAR_CITIES:START -->
<div class="card">
<h2 class="sectionTitle">Popular cities in {state_name}</h2>
<ul class="gridList">
{lis}
</ul>
</div>
<!-- POPULAR_CITIES:END -->"""

    if "<!-- POPULAR_CITIES:ANCHOR -->" in html:
        html = html.replace("<!-- POPULAR_CITIES:ANCHOR -->", f"{block}\n\n    <!-- POPULAR_CITIES:ANCHOR -->")
    elif '<div class="footer">' in html:
        html = html.replace('<div class="footer">', f"{block}\n\n    <div class=\"footer\">", 1)
    else:
        container_end = html.find("</div>")
        if container_end == -1:
            html = html + "\n" + block
        else:
            html = html[:container_end] + "\n" + block + "\n" + html[container_end:]

    idx.write_text(html, encoding="utf-8")
    return True

def main():
    ap = argparse.ArgumentParser(description="Publish a safe batch of popular city pages each day.")
    ap.add_argument("--max", type=int, default=12, help="Max new city pages to create per run (default 12).")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing city pages.")
    ap.add_argument("--inject", dest="inject", action="store_true", help="Inject popular city blocks into state index pages (default).")
    ap.add_argument("--no-inject", dest="inject", action="store_false", help="Skip injecting city blocks into state index pages.")
    ap.set_defaults(inject=True)
    ap.add_argument("--force", action="store_true", help="Run even if already ran today (UTC).")
    args = ap.parse_args()

    run_log = load_json(RUN_LOG, {})
    if already_ran_today(run_log) and not args.force:
        print(f"Already ran today (UTC {utc_date_str()}). Use --force to run again.")
        return

    popular = read_popular_list()

    created = 0
    considered = 0

    # Round-robin across sections to keep growth balanced
    section_i = 0

    while created < args.max and considered < len(popular) * len(SECTIONS):
        st, city = popular[considered % len(popular)]
        section = SECTIONS[section_i % len(SECTIONS)]
        section_i += 1
        considered += 1

        ensure_state_index(section, st)

        city_slug = slugify(city)
        folder = Path(section) / st / city_slug
        ensure_dir(folder)
        idx = folder / "index.html"

        if idx.exists() and not args.overwrite:
            continue

        idx.write_text(city_page_html(section, st, city), encoding="utf-8")
        created += 1
        print(f"Created: /{section}/{st}/{city_slug}/")

    injected = 0
    if args.inject:
        # inject once per state per section if not already injected
        for section in SECTIONS:
            for st in US_STATES.keys():
                if inject_city_block(section, st, popular):
                    injected += 1

    run_log["last_run_utc"] = utc_date_str()
    run_log.setdefault("history", [])
    run_log["history"].append({
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "created": created,
        "max": args.max,
        "inject": bool(args.inject),
    })
    if len(run_log["history"]) > 200:
        run_log["history"] = run_log["history"][-200:]
    save_json(RUN_LOG, run_log)

    print(f"Done. New city pages: {created}. State pages injected: {injected}.")
    print("Next: run make-site.py to rebuild sitemap.xml and robots.txt, then upload to Cloudflare.")

if __name__ == "__main__":
    main()
