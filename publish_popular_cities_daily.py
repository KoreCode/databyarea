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
from html import escape

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

COUNTY_CITY_MAP = {
    "california": {
        "Los Angeles County": ["Los Angeles", "Long Beach", "Glendale", "Lancaster"],
        "San Diego County": ["San Diego", "Chula Vista", "Oceanside", "Escondido"],
        "Orange County": ["Anaheim", "Santa Ana", "Irvine", "Huntington Beach"],
    },
    "texas": {
        "Harris County": ["Houston", "Pasadena", "Baytown", "League City"],
        "Dallas County": ["Dallas", "Irving", "Garland", "Mesquite"],
        "Travis County": ["Austin", "Round Rock", "Pflugerville", "Cedar Park"],
        "Bexar County": ["San Antonio"],
    },
    "florida": {
        "Miami-Dade County": ["Miami", "Hialeah", "Miami Gardens", "Homestead"],
        "Hillsborough County": ["Tampa"],
        "Orange County": ["Orlando"],
    },
    "illinois": {
        "Cook County": ["Chicago", "Cicero", "Evanston", "Skokie"],
    },
    "new-york": {
        "New York County": ["New York"],
        "Kings County": ["Brooklyn"],
        "Queens County": ["Queens"],
    },
    "arizona": {
        "Maricopa County": ["Phoenix", "Mesa", "Chandler", "Gilbert", "Scottsdale"],
    },
    "pennsylvania": {
        "Philadelphia County": ["Philadelphia"],
        "Allegheny County": ["Pittsburgh"],
    },
    "washington": {
        "King County": ["Seattle", "Bellevue", "Kent", "Renton"],
    },
    "nevada": {
        "Clark County": ["Las Vegas", "Henderson", "North Las Vegas"],
    },
    "utah": {
        "Salt Lake County": ["Salt Lake City", "West Valley City", "Sandy"],
    },
    "north-carolina": {
        "Wake County": ["Raleigh", "Cary"],
    },
    "ohio": {
        "Franklin County": ["Columbus"],
        "Cuyahoga County": ["Cleveland"],
    },
    "michigan": {
        "Wayne County": ["Detroit", "Dearborn", "Livonia"],
    },
}

MINNESOTA_UTILITY_BENCHMARK_2024 = {
    "source_year": 2024,
    "price_cents_per_kwh": 15.45,
    "monthly_kwh": 712,
    "monthly_bill_usd": 110.06,
    "customers": 2_581_180,
    "commercial_price_cents_per_kwh": 12.15,
    "industrial_price_cents_per_kwh": 9.15,
    "us_price_cents_per_kwh": 16.48,
    "us_monthly_kwh": 863,
    "us_monthly_bill_usd": 142.26,
    "price_rank_label": "below U.S. average",
    "source_note": (
        "U.S. Energy Information Administration (EIA), forms EIA-861 schedules 4A-4D, "
        "EIA-861S, EIA-861U. 2024 annual tables published in 2026."
    ),
}


LOCAL_CITY_PROFILE_OVERRIDES = {
    ("minnesota", "kiester"): {
        "stateCode": "MN",
        "county": "Faribault County",
        "zip": "56051",
        "lat": 43.5426,
        "lng": -94.4986,
        "population": "485",
        "medianHome": "$115k",
        "medianIncome": "$52.4k",
        "schools": "B+ Rating",
        "electricityAvg": "$115/mo avg",
        "gasAvg": "$70/mo avg",
        "waterAvg": "$55/mo avg",
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

    if section == "utility-costs":
        city_key = (state_slug, city_slug)
        base_profile = {
            "stateCode": state_slug[:2].upper(),
            "county": f"{state_name} County",
            "zip": "00000",
            "lat": 44.95,
            "lng": -93.09,
            "population": "—",
            "medianHome": "—",
            "medianIncome": "—",
            "schools": "—",
            "electricityAvg": "$110/mo avg",
            "gasAvg": "$62/mo avg",
            "waterAvg": "$48/mo avg",
        }
        profile = {**base_profile, **LOCAL_CITY_PROFILE_OVERRIDES.get(city_key, {})}
        profile_json = json.dumps(profile, ensure_ascii=False)
        desc = (
            f"{city_name}, {state_name} localized utility and cost-of-living overview with interactive charts, "
            "map, and property-tax context."
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{city_name}, {state_name} Localized Data | {SITE_NAME}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="{canonical}">
  <link rel="stylesheet" href="{CSS_PATH}">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
  <style>
    .city-shell {{ max-width: 1140px; margin: 0 auto; }}
    .city-nav {{ display:flex; align-items:center; justify-content:space-between; padding: 18px 12px; background:#fff; }}
    .city-nav .links {{ display:flex; gap:28px; font-weight:500; }}
    .mobile-header {{ display:none; position:sticky; top:0; z-index:50; background:#2563eb; color:#fff; padding:14px 16px; align-items:center; justify-content:space-between; }}
    .hero-band {{ background:linear-gradient(90deg,#3b82f6,#99f6e4); padding:28px 12px; }}
    .hero-title {{ font-size:52px; margin:0; text-align:center; }}
    .hero-sub {{ margin:2px 0 0; text-align:center; color:#0f172a; }}
    .pill-search {{ margin:14px auto 0; max-width:640px; background:#fff; border:1px solid #94a3b8; border-radius:999px; padding:12px 18px; display:flex; gap:10px; align-items:center; position:relative; }}
    .pill-search input {{ border:0; outline:0; width:100%; font-size:30px; }}
    .autocomplete-menu {{ position:absolute; top:56px; left:0; right:0; background:#fff; border:1px solid #cbd5e1; border-radius:12px; box-shadow:0 10px 24px rgba(15,23,42,.12); display:none; max-height:220px; overflow:auto; }}
    .autocomplete-menu button {{ width:100%; text-align:left; border:0; background:transparent; padding:10px 14px; cursor:pointer; }}
    .autocomplete-menu button:hover {{ background:#eff6ff; }}
    .city-grid {{ display:grid; grid-template-columns: 1fr 1.3fr 1fr; gap:16px; padding:20px 12px 28px; }}
    .data-card {{ background:#fff; border:1px solid #d1d5db; border-radius:14px; box-shadow:0 8px 18px rgba(15,23,42,.06); padding:14px; }}
    .utility-row {{ display:grid; grid-template-columns:1fr auto; gap:10px; align-items:center; padding:10px 0; border-bottom:1px solid #e5e7eb; }}
    .utility-row:last-child {{ border-bottom:0; }}
    .progress-track {{ width:100%; height:12px; border-radius:999px; background:#e5e7eb; position:relative; overflow:hidden; }}
    .progress-bar {{ height:100%; border-radius:999px; }}
    .bar-label {{ display:flex; justify-content:space-between; margin:10px 0 6px; }}
    .mobile-glance {{ display:none; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px; }}
    .glance-item {{ border:1px solid #d6dee8; border-radius:10px; padding:10px; background:#fff; box-shadow:0 4px 10px rgba(15,23,42,.08); }}
    .deep-dive {{ display:none; margin:12px; }}
    .deep-dive details {{ border:1px solid #d6dee8; border-radius:10px; margin:8px 0; background:#fff; overflow:hidden; }}
    .deep-dive summary {{ padding:12px; cursor:pointer; font-weight:600; }}
    .deep-dive .inner {{ padding:0 12px 12px; color:#475569; }}
    #city-map {{ width:100%; min-height:320px; border-radius:14px; }}
    .map-expand {{ margin-top:8px; width:100%; border:1px solid #93c5fd; background:#eff6ff; border-radius:10px; padding:8px; font-weight:600; }}
    .map-fullscreen {{ position:fixed; inset:0; z-index:999; padding:8px; background:#fff; }}
    @media (max-width: 900px) {{
      .city-nav {{ display:none; }}
      .mobile-header {{ display:flex; }}
      .hero-band {{ background:#fff; border-bottom:1px solid #e5e7eb; padding:12px; }}
      .hero-title {{ font-size:22px; text-align:left; }}
      .hero-sub {{ text-align:left; }}
      .pill-search {{ margin:8px 0 0; }}
      .pill-search input {{ font-size:22px; }}
      .city-grid {{ grid-template-columns:1fr; padding:12px; }}
      .mobile-glance {{ display:grid; }}
      .deep-dive {{ display:block; }}
    }}
  </style>
</head>
<body>
  <div class="city-shell">
    <header class="city-nav">
      <div class="brand"><img src="/assets/logo.png" class="logo" alt="{SITE_NAME} logo"><strong>DataByArea.com</strong></div>
      <nav class="links"><a href="/utility-costs/">Utilities</a><a href="/cost-of-living/">Cost of Living</a><a href="/property-taxes/">Property Taxes</a><a href="/about/">About</a></nav>
    </header>
    <header class="mobile-header"><button aria-label="Open navigation">☰</button><strong>DataByArea</strong><button aria-label="Search">⌕</button></header>
    <section class="hero-band">
      <h1 class="hero-title">{city_name}, {profile["stateCode"]}</h1>
      <p class="hero-sub">{profile["county"]} · Zip: {profile["zip"]}</p>
      <div class="pill-search">
        <span aria-hidden="true">🔎</span>
        <input id="local-search" type="search" placeholder="Find Local Area Data: Enter a City or Zip Code">
        <div id="autocomplete" class="autocomplete-menu"></div>
      </div>
      <div class="mobile-glance">
        <div class="glance-item"><small>Population</small><div><strong>{profile["population"]}</strong></div></div>
        <div class="glance-item"><small>Med. Home</small><div><strong>{profile["medianHome"]}</strong></div></div>
        <div class="glance-item"><small>Income</small><div><strong>{profile["medianIncome"]}</strong></div></div>
        <div class="glance-item"><small>Schools</small><div><strong>{profile["schools"]}</strong></div></div>
      </div>
    </section>
    <main class="city-grid">
      <section class="data-card">
        <h2>Utilities Overview</h2>
        <div class="utility-row"><div><strong>Electricity</strong><canvas id="chart-electricity" height="36"></canvas></div><div>{profile["electricityAvg"]}</div></div>
        <div class="utility-row"><div><strong>Natural Gas</strong><canvas id="chart-gas" height="36"></canvas></div><div>{profile["gasAvg"]}</div></div>
        <div class="utility-row"><div><strong>Water/Sewer</strong><canvas id="chart-water" height="36"></canvas></div><div>{profile["waterAvg"]}</div></div>
      </section>
      <section class="data-card">
        <div id="city-map"></div>
        <button id="expand-map" class="map-expand" type="button">Expand map</button>
      </section>
      <aside>
        <section class="data-card">
          <h2>Cost of Living Metrics</h2>
          <div class="bar-label"><span>Total Index</span><strong>92</strong></div>
          <div class="progress-track" title="6-month trend: 90, 91, 91, 92, 92, 92"><div class="progress-bar" style="width:70%; background:#3b82f6;"></div></div>
          <div class="bar-label"><span>Housing</span><strong>85</strong></div>
          <div class="progress-track" title="6-month trend: 83, 84, 84, 85, 85, 85"><div class="progress-bar" style="width:64%; background:#f59e0b;"></div></div>
          <div class="bar-label"><span>Groceries</span><strong>98</strong></div>
          <div class="progress-track" title="6-month trend: 97, 97, 98, 98, 98, 98"><div class="progress-bar" style="width:74%; background:#10b981;"></div></div>
          <div class="bar-label"><span>Transportation</span><strong>101</strong></div>
          <div class="progress-track" title="6-month trend: 99, 99, 100, 100, 101, 101"><div class="progress-bar" style="width:77%; background:#06b6d4;"></div></div>
        </section>
        <section class="data-card" style="margin-top:12px;">
          <h2>Property Tax Information</h2>
          <p><strong>{profile["county"]} Property Taxes</strong></p>
          <p>Median Amount: $1,850/year</p>
          <p><a href="/property-taxes/{state_slug}/">View Property Tax Calculator ↗</a></p>
        </section>
      </aside>
    </main>
    <section class="deep-dive">
      <details><summary>Demographics</summary><div class="inner">Population trends, age mix, household size and migration snapshots for {city_name}.</div></details>
      <details><summary>Real Estate & Housing</summary><div class="inner">Median home, rent-to-income, vacancy, and appreciation trend points.</div></details>
      <details><summary>Local Economy</summary><div class="inner">Employment sectors, commute patterns, and income growth indicators.</div></details>
      <details><summary>Crime & Safety</summary><div class="inner">Safety scoring and incident mix with annual comparison context.</div></details>
    </section>
  </div>
  <script>window.__CITY_PROFILE__ = {profile_json};</script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <script>
    (function() {{
      const p = window.__CITY_PROFILE__ || {{}};
      const sparkline = (id, points, label) => {{
        const ctx = document.getElementById(id);
        if (!ctx || !window.Chart) return;
        new Chart(ctx, {{
          type: "line",
          data: {{ labels: ["M1","M2","M3","M4","M5","M6"], datasets: [{{ data: points, borderColor:"#2563eb", borderWidth:2, fill:false, tension:.35, pointRadius:0 }}] }},
          options: {{ responsive:true, maintainAspectRatio:false, plugins: {{ legend: {{ display:false }}, tooltip: {{ callbacks: {{ label: (c) => label + ": $" + c.raw }} }} }}, scales: {{ x: {{ display:false }}, y: {{ display:false }} }} }}
        }});
      }};
      sparkline("chart-electricity", [108,112,110,118,113,115], "Electricity");
      sparkline("chart-gas", [58,61,63,76,68,70], "Natural Gas");
      sparkline("chart-water", [52,54,49,58,55,55], "Water/Sewer");

      if (window.L) {{
        const map = L.map("city-map", {{ scrollWheelZoom: false }}).setView([p.lat || 44.95, p.lng || -93.09], 11);
        L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{ maxZoom: 18, attribution: "&copy; OpenStreetMap contributors" }}).addTo(map);
        L.marker([p.lat || 44.95, p.lng || -93.09]).addTo(map);
        const expandBtn = document.getElementById("expand-map");
        const mapNode = document.getElementById("city-map");
        expandBtn?.addEventListener("click", () => {{
          mapNode.classList.toggle("map-fullscreen");
          expandBtn.textContent = mapNode.classList.contains("map-fullscreen") ? "Collapse map" : "Expand map";
          map.invalidateSize();
        }});
      }}

      const search = document.getElementById("local-search");
      const menu = document.getElementById("autocomplete");
      let timer = null;
      const fallback = [
        {{ label: "Kiester, MN 56051", href: "/utility-costs/minnesota/kiester/" }},
        {{ label: "Minneapolis, MN 55401", href: "/utility-costs/minnesota/minneapolis/" }},
        {{ label: "Des Moines, IA 50309", href: "/utility-costs/iowa/des-moines/" }}
      ];
      const renderMenu = (items) => {{
        menu.innerHTML = items.map((i) => `<button type="button" data-href="${{i.href}}">${{i.label}}</button>`).join("");
        menu.style.display = items.length ? "block" : "none";
      }};
      search?.addEventListener("input", (e) => {{
        clearTimeout(timer);
        timer = setTimeout(async () => {{
          const q = e.target.value.trim();
          if (q.length < 2) {{ menu.style.display = "none"; return; }}
          try {{
            const resp = await fetch(`/api/locations/autocomplete?q=${{encodeURIComponent(q)}}`);
            if (!resp.ok) throw new Error("autocomplete failed");
            const data = await resp.json();
            renderMenu(data.items || []);
          }} catch (_) {{
            renderMenu(fallback.filter((i) => i.label.toLowerCase().includes(q.toLowerCase())));
          }}
        }}, 150);
      }});
      menu?.addEventListener("click", (e) => {{
        const btn = e.target.closest("button[data-href]");
        if (btn) window.location.href = btn.dataset.href;
      }});
    }})();
  </script>
  <script defer src="/assets/version-footer.js"></script>
</body>
</html>
"""

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

def read_minnesota_city_store() -> dict[str, str]:
    csv_path = Path("data/minnesota_utility_city_store.csv")
    slug_to_city: dict[str, str] = {}
    if not csv_path.exists():
        return slug_to_city
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug = (row.get("city_slug") or "").strip().lower()
            city = (row.get("city") or "").strip()
            if slug and city:
                slug_to_city[slug] = city
    return slug_to_city


def refresh_existing_utility_city_pages(state_slug_filter: str | None = None) -> int:
    minnesota_city_map = read_minnesota_city_store()
    refreshed = 0
    for path in Path("utility-costs").glob("*/*/index.html"):
        state_slug = path.parts[1]
        if state_slug_filter and state_slug != state_slug_filter:
            continue
        city_slug = path.parts[2]
        if state_slug == "minnesota":
            city_name = minnesota_city_map.get(city_slug, city_slug.replace("-", " ").title())
        else:
            city_name = city_slug.replace("-", " ").title()
        path.write_text(city_page_html("utility-costs", state_slug, city_name), encoding="utf-8")
        refreshed += 1
    return refreshed

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

def _existing_city_names_for_state(section: str, state_slug: str) -> list[str]:
    """
    Return city names from already-published city folders for this state/section.
    """
    state_dir = Path(section) / state_slug
    if not state_dir.exists():
        return []
    names: list[str] = []
    for city_index in sorted(state_dir.glob("*/index.html")):
        city_slug = city_index.parent.name
        if city_slug == "index":
            continue
        if city_slug.endswith(("-county", "-parish", "-borough", "-census-area")):
            continue
        names.append(city_slug.replace("-", " ").title())
    return names


def _merged_city_names(state_slug: str, city_pairs: list[tuple[str, str]], section: str, max_links: int) -> list[str]:
    """
    Merge cities from CSV with cities already published on disk, preserving order and uniqueness.
    """
    csv_cities = [city for st, city in city_pairs if st == state_slug]
    existing_cities = _existing_city_names_for_state(section, state_slug)

    merged: list[str] = []
    seen: set[str] = set()
    for city in csv_cities + existing_cities:
        city_clean = city.strip()
        if not city_clean:
            continue
        key = slugify(city_clean)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(city_clean)
    return merged[:max_links]


def inject_city_block(section: str, state_slug: str, city_pairs: list[tuple[str,str]], max_links: int = 24) -> bool:
    idx = Path(section) / state_slug / "index.html"
    if not idx.exists():
        return False
    html = idx.read_text(encoding="utf-8", errors="ignore")

    state_name = US_STATES[state_slug]
    cities = _merged_city_names(state_slug, city_pairs, section, max_links)
    if not cities:
        return False

    lis = "\n".join(
        f'<li><a class="cityLink" href="/{section}/{state_slug}/{slugify(c)}/">{escape(c)}</a></li>' for c in cities
    )

    block = f"""<!-- POPULAR_CITIES:START -->
<div class="card">
<h2 class="sectionTitle">Popular cities in {state_name}</h2>
<p class="cityListMeta">Browse {len(cities)} total city pages in {state_name}.</p>
<ul class="gridList cityGrid">
{lis}
</ul>
</div>
<!-- POPULAR_CITIES:END -->"""

    if "<!-- POPULAR_CITIES:START -->" in html and "<!-- POPULAR_CITIES:END -->" in html:
        html = re.sub(
            r"<!-- POPULAR_CITIES:START -->.*?<!-- POPULAR_CITIES:END -->",
            block,
            html,
            flags=re.DOTALL,
        )
    elif "<!-- POPULAR_CITIES:ANCHOR -->" in html:
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


def county_page_html(section: str, state_slug: str, county_name: str, county_cities: list[str]) -> str:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    state_name = US_STATES.get(state_slug, state_slug.replace("-", " ").title())
    section_title = SECTION_META[section]["title"]
    county_slug = slugify(county_name)
    canonical = f"{SITE_URL}/{section}/{state_slug}/{county_slug}/"
    desc = (
        f"County-level {section_title.lower()} guide for {county_name}, {state_name}, "
        f"including city pages and comparison links."
    )
    city_items = "\n".join(
        f'<li class="item"><a href="/{section}/{state_slug}/{slugify(city)}/">{escape(city)}</a></li>'
        for city in county_cities
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{section_title} in {county_name}, {state_name} | {SITE_NAME}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="{canonical}">
  <link rel="stylesheet" href="{CSS_PATH}">
</head>
<body>
  <div class="container">
    <div class="hero">
      <h1>{section_title} in {county_name}, {state_name}</h1>
      <p>{desc}</p>
      <div class="breadcrumbs">
        <a href="/">Home</a> › <a href="/{section}/">{section_title}</a> › <a href="/{section}/{state_slug}/">{state_name}</a> › <span>{county_name}</span>
      </div>
    </div>

    <div class="card">
      <h2>Cities in {county_name}</h2>
      <p>This county page lists the city pages currently available for this county.</p>
      <ul class="list">
        {city_items}
      </ul>
    </div>

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


def ensure_county_pages(section: str, state_slug: str) -> int:
    county_map = COUNTY_CITY_MAP.get(state_slug, {})
    written = 0
    for county_name, county_cities in county_map.items():
        county_slug = slugify(county_name)
        folder = Path(section) / state_slug / county_slug
        ensure_dir(folder)
        idx = folder / "index.html"
        html = county_page_html(section, state_slug, county_name, county_cities)
        current = idx.read_text(encoding="utf-8", errors="ignore") if idx.exists() else None
        if current != html:
            idx.write_text(html, encoding="utf-8")
            written += 1
    return written


def inject_county_block(section: str, state_slug: str, max_links: int = 12) -> bool:
    idx = Path(section) / state_slug / "index.html"
    if not idx.exists():
        return False
    county_map = COUNTY_CITY_MAP.get(state_slug)
    if not county_map:
        return False

    html = idx.read_text(encoding="utf-8", errors="ignore")
    state_name = US_STATES[state_slug]
    county_items = list(county_map.items())[:max_links]
    lis = "\n".join(
        (
            f'<li><a class="cityLink" href="/{section}/{state_slug}/{slugify(county_name)}/">'
            f'{escape(county_name)}</a> '
            f'<span class="mutedSmall">({len(cities)} {"city" if len(cities) == 1 else "cities"})</span></li>'
        )
        for county_name, cities in county_items
    )
    block = f"""<!-- COUNTY_PAGES:START -->
<div class="card">
<h2 class="sectionTitle">Counties in {state_name}</h2>
<p class="cityListMeta">Browse {len(county_items)} county pages with city-level links.</p>
<ul class="gridList cityGrid">
{lis}
</ul>
</div>
<!-- COUNTY_PAGES:END -->"""

    if "<!-- COUNTY_PAGES:START -->" in html and "<!-- COUNTY_PAGES:END -->" in html:
        html = re.sub(
            r"<!-- COUNTY_PAGES:START -->.*?<!-- COUNTY_PAGES:END -->",
            block,
            html,
            flags=re.DOTALL,
        )
    elif "<!-- COUNTY_PAGES:ANCHOR -->" in html:
        html = html.replace("<!-- COUNTY_PAGES:ANCHOR -->", f"{block}\n\n    <!-- COUNTY_PAGES:ANCHOR -->")
    elif "<!-- POPULAR_CITIES:ANCHOR -->" in html:
        html = html.replace("<!-- POPULAR_CITIES:ANCHOR -->", f"{block}\n\n    <!-- POPULAR_CITIES:ANCHOR -->")
    elif '<div class="footer">' in html:
        html = html.replace('<div class="footer">', f"{block}\n\n    <div class=\"footer\">", 1)
    else:
        html = html + "\n" + block

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
    ap.add_argument(
        "--refresh-utility-city-pages",
        action="store_true",
        help="Rewrite all existing /utility-costs/<state>/<city>/ pages with the latest utility city template.",
    )
    ap.add_argument(
        "--state",
        type=str,
        default=None,
        help="Optional state slug filter for refresh modes (example: minnesota).",
    )
    args = ap.parse_args()

    if args.refresh_utility_city_pages:
        state_filter = slugify(args.state) if args.state else None
        refreshed = refresh_existing_utility_city_pages(state_filter)
        print(f"Refreshed utility city pages: {refreshed}.")
        return

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
    county_injected = 0
    county_pages_written = 0
    if args.inject:
        # inject once per state per section
        for section in SECTIONS:
            for st in US_STATES.keys():
                county_pages_written += ensure_county_pages(section, st)
                if inject_county_block(section, st):
                    county_injected += 1
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

    print(
        f"Done. New city pages: {created}. "
        f"State pages with county blocks: {county_injected}. "
        f"County pages written: {county_pages_written}. "
        f"State pages with city blocks: {injected}."
    )
    print("Next: run make-site.py to rebuild sitemap.xml and robots.txt, then upload to Cloudflare.")

if __name__ == "__main__":
    main()
