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
import urllib.parse
import urllib.request
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from html import escape

SITE_NAME = "DataByArea"
SITE_URL = "https://databyarea.com"
CSS_PATH = "/assets/styles.css"
DEFAULT_CENSUS_API_KEY = "a8fbaff5b31f948e263efac8e6c03b9ad8deeea0"
ACS_DATASET = "2023/acs/acs5"

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

STATE_FIPS_BY_SLUG = {
    "alabama": "01", "alaska": "02", "arizona": "04", "arkansas": "05", "california": "06",
    "colorado": "08", "connecticut": "09", "delaware": "10", "florida": "12", "georgia": "13",
    "hawaii": "15", "idaho": "16", "illinois": "17", "indiana": "18", "iowa": "19",
    "kansas": "20", "kentucky": "21", "louisiana": "22", "maine": "23", "maryland": "24",
    "massachusetts": "25", "michigan": "26", "minnesota": "27", "mississippi": "28", "missouri": "29",
    "montana": "30", "nebraska": "31", "nevada": "32", "new-hampshire": "33", "new-jersey": "34",
    "new-mexico": "35", "new-york": "36", "north-carolina": "37", "north-dakota": "38", "ohio": "39",
    "oklahoma": "40", "oregon": "41", "pennsylvania": "42", "rhode-island": "44", "south-carolina": "45",
    "south-dakota": "46", "tennessee": "47", "texas": "48", "utah": "49", "vermont": "50",
    "virginia": "51", "washington": "53", "west-virginia": "54", "wisconsin": "55", "wyoming": "56",
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

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = s.replace(".", "")
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s


def _normalize_place_name(name: str) -> str:
    base = name.split(",")[0].strip().lower()
    for suffix in (
        " city", " town", " village", " borough", " municipality", " metro government",
        " urban county", " consolidated government", " cdp",
    ):
        if base.endswith(suffix):
            base = base[: -len(suffix)].strip()
    base = base.replace("saint ", "st ")
    return slugify(base)


def _safe_int(v: str | None) -> int | None:
    if v in (None, "", "-666666666", "-888888888", "-999999999"):
        return None
    try:
        return int(float(v))
    except Exception:
        return None


def _census_get_rows(url: str) -> list[list[str]]:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    return payload if isinstance(payload, list) and len(payload) > 1 else []


@lru_cache(maxsize=64)
def _census_state_property_tax_rows(state_slug: str, api_key: str) -> dict[str, dict]:
    state_fips = STATE_FIPS_BY_SLUG.get(state_slug)
    if not state_fips:
        return {}
    vars_ = ["NAME", "B25103_001E", "B25077_001E", "B19013_001E"]
    query = {
        "get": ",".join(vars_),
        "for": "place:*",
        "in": f"state:{state_fips}",
        "key": api_key,
    }
    url = f"https://api.census.gov/data/{ACS_DATASET}?{urllib.parse.urlencode(query)}"
    rows = _census_get_rows(url)
    if not rows:
        return {}

    header = rows[0]
    i_name = header.index("NAME")
    i_tax = header.index("B25103_001E")
    i_value = header.index("B25077_001E")
    i_income = header.index("B19013_001E")
    i_place = header.index("place")

    out: dict[str, dict] = {}
    for row in rows[1:]:
        name = row[i_name]
        city_key = _normalize_place_name(name)
        med_tax = _safe_int(row[i_tax])
        med_home_value = _safe_int(row[i_value])
        med_income = _safe_int(row[i_income])
        effective_rate_pct = None
        if med_tax and med_home_value and med_home_value > 0:
            effective_rate_pct = round((med_tax / med_home_value) * 100, 3)
        out[city_key] = {
            "city_name": name.split(",")[0].strip(),
            "place_fips": row[i_place],
            "median_property_tax_usd": med_tax,
            "median_home_value_usd": med_home_value,
            "median_household_income_usd": med_income,
            "effective_property_tax_rate_pct": effective_rate_pct,
            "dataset": ACS_DATASET,
        }
    return out


def get_city_property_tax_profile(state_slug: str, city_name: str) -> dict | None:
    api_key = DEFAULT_CENSUS_API_KEY
    data = _census_state_property_tax_rows(state_slug, api_key)
    if not data:
        return None
    key = _normalize_place_name(city_name)
    value = data.get(key)
    if value:
        return value
    alt = slugify(city_name.lower().replace("saint ", "st "))
    return data.get(alt)

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
        mn = MINNESOTA_UTILITY_BENCHMARK_2024
        minnesota_detail_html = ""
        if state_slug == "minnesota":
            minnesota_detail_html = f"""
    <h2>Minnesota Electricity Benchmarks ({mn["source_year"]} EIA)</h2>
    <p>Statewide electricity data is shown below so you can convert utility planning to <strong>cost per kWh</strong> and bill-impact math.</p>
    <table>
      <thead>
        <tr>
          <th>Benchmark</th>
          <th>Minnesota</th>
          <th>U.S.</th>
          <th>Why it matters</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>Average residential price</td><td>{mn["price_cents_per_kwh"]:.2f}¢/kWh</td><td>{mn["us_price_cents_per_kwh"]:.2f}¢/kWh</td><td>Rate baseline for appliance and heating-electricity planning</td></tr>
        <tr><td>Average residential monthly usage</td><td>{mn["monthly_kwh"]} kWh</td><td>{mn["us_monthly_kwh"]} kWh</td><td>Usage benchmark for seasonal budget stress tests</td></tr>
        <tr><td>Average residential monthly bill</td><td>${mn["monthly_bill_usd"]:.2f}</td><td>${mn["us_monthly_bill_usd"]:.2f}</td><td>Fast renter/owner utility budget anchor</td></tr>
        <tr><td>Commercial average price</td><td>{mn["commercial_price_cents_per_kwh"]:.2f}¢/kWh</td><td>—</td><td>Small business and mixed-use property context</td></tr>
        <tr><td>Industrial average price</td><td>{mn["industrial_price_cents_per_kwh"]:.2f}¢/kWh</td><td>—</td><td>Regional load and local economic-rate context</td></tr>
      </tbody>
    </table>

    <h2>Utility Snapshot Graph (Minnesota vs U.S.)</h2>
    <p>The mini chart compares state and national utility intensity (price, usage, and bill) for quick decision support.</p>
    <svg viewBox="0 0 620 230" role="img" aria-label="Minnesota vs United States electricity benchmark chart" style="max-width:100%;height:auto;border:1px solid #e5e7eb;border-radius:10px;background:#fff">
      <line x1="60" y1="190" x2="600" y2="190" stroke="#cbd5e1" />
      <line x1="60" y1="40" x2="60" y2="190" stroke="#cbd5e1" />
      <text x="80" y="28" font-size="12" fill="#334155">Residential price (¢/kWh)</text>
      <rect x="80" y="108" width="120" height="20" fill="#0ea5e9" />
      <rect x="80" y="132" width="127" height="20" fill="#94a3b8" />
      <text x="205" y="123" font-size="11" fill="#0f172a">MN {mn["price_cents_per_kwh"]:.2f}</text>
      <text x="212" y="147" font-size="11" fill="#0f172a">US {mn["us_price_cents_per_kwh"]:.2f}</text>

      <text x="260" y="28" font-size="12" fill="#334155">Monthly usage (kWh)</text>
      <rect x="260" y="85" width="120" height="20" fill="#0ea5e9" />
      <rect x="260" y="61" width="145" height="20" fill="#94a3b8" />
      <text x="385" y="100" font-size="11" fill="#0f172a">MN {mn["monthly_kwh"]}</text>
      <text x="410" y="76" font-size="11" fill="#0f172a">US {mn["us_monthly_kwh"]}</text>

      <text x="430" y="28" font-size="12" fill="#334155">Monthly bill ($)</text>
      <rect x="430" y="99" width="120" height="20" fill="#0ea5e9" />
      <rect x="430" y="66" width="155" height="20" fill="#94a3b8" />
      <text x="555" y="114" font-size="11" fill="#0f172a">MN {mn["monthly_bill_usd"]:.0f}</text>
      <text x="590" y="81" font-size="11" fill="#0f172a">US {mn["us_monthly_bill_usd"]:.0f}</text>

      <text x="80" y="212" font-size="11" fill="#475569">Blue = Minnesota</text>
      <text x="210" y="212" font-size="11" fill="#475569">Gray = U.S. average</text>
    </svg>

    <h2>Useful Minnesota Utility Details</h2>
    <ul class="list">
      <li class="item"><strong>Customer base:</strong> {mn["customers"]:,} residential electricity customers in annual reporting.</li>
      <li class="item"><strong>Positioning:</strong> Minnesota residential electricity pricing is {mn["price_rank_label"]} for the same reporting year.</li>
      <li class="item"><strong>Budget conversion:</strong> Every additional 100 kWh/month is about ${(mn["price_cents_per_kwh"]):.2f} at the statewide average price.</li>
      <li class="item"><strong>Source:</strong> {mn["source_note"]}</li>
    </ul>
"""
        desc = (
            f"{city_name}, {state_name} utility cost guide with electricity, gas, water, sewer, trash, "
            "internet, and mobile cost ratings plus monthly budget ranges."
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{city_name}, {state_name} Utility Cost by Category (Rated) | {SITE_NAME}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="{canonical}">
  <link rel="stylesheet" href="{CSS_PATH}">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {{
        "@type": "Question",
        "name": "What utilities are included in this {city_name}, {state_name} cost breakdown?",
        "acceptedAnswer": {{
          "@type": "Answer",
          "text": "This page includes electricity, natural gas, water, sewer, trash collection, home internet, and mobile service cost ratings."
        }}
      }},
      {{
        "@type": "Question",
        "name": "How should I use utility cost ratings for moving decisions?",
        "acceptedAnswer": {{
          "@type": "Answer",
          "text": "Use the ratings as a planning baseline, then confirm with local utility providers, property managers, and recent household bills before signing a lease or buying."
        }}
      }},
      {{
        "@type": "Question",
        "name": "What changes monthly utility bills the most?",
        "acceptedAnswer": {{
          "@type": "Answer",
          "text": "Seasonal weather, home size and insulation, household occupancy, appliance efficiency, and provider rate plans usually drive the largest monthly bill changes."
        }}
      }}
    ]
  }}
  </script>
</head>
<body>
  <div class="container">
    <h1>{city_name}, {state_name} Utility Cost by Category</h1>
    <p class="lede">Use this city guide to compare utility cost ratings and monthly budget ranges before you rent, buy, or relocate.</p>

    <h2>Utility Cost Ratings for {city_name}</h2>
    <p>Ratings below are built for quick comparison and budget planning. Confirm final rates with local providers and your specific property profile.</p>
    <table>
      <thead>
        <tr>
          <th>Utility Category</th>
          <th>Typical Monthly Range</th>
          <th>Cost Rating</th>
          <th>What Moves This Cost</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>Electricity</td><td>$90-$220</td><td>Medium</td><td>Cooling load, heating fuel type, insulation, peak-hour usage</td></tr>
        <tr><td>Natural Gas / Heating Fuel</td><td>$35-$180</td><td>Medium</td><td>Winter climate, furnace efficiency, water heating source</td></tr>
        <tr><td>Water</td><td>$35-$95</td><td>Low to Medium</td><td>Household size, irrigation, fixture flow rates</td></tr>
        <tr><td>Sewer & Wastewater</td><td>$30-$85</td><td>Medium</td><td>Municipal fee structures, seasonal usage tiers</td></tr>
        <tr><td>Trash / Recycling</td><td>$20-$60</td><td>Low</td><td>Local service contracts, container size, add-on pickup</td></tr>
        <tr><td>Home Internet</td><td>$45-$95</td><td>Medium</td><td>Speed tier, fiber availability, promo expiration</td></tr>
        <tr><td>Mobile Service (1 line)</td><td>$35-$90</td><td>Medium</td><td>Carrier mix, unlimited plans, taxes and fees</td></tr>
      </tbody>
    </table>

    <h2>Estimated Total Utility Budget Bands</h2>
    <ul class="list">
      <li class="item"><strong>Studio / 1-bed renter:</strong> $180-$420 per month depending on season and internet tier.</li>
      <li class="item"><strong>2-3 bedroom household:</strong> $320-$680 per month with moderate energy usage.</li>
      <li class="item"><strong>Larger single-family home:</strong> $520-$1,050 per month in high-usage months.</li>
    </ul>

    <h2>Utility Cost Detail Checklist (High-Intent Comparison)</h2>
    <ul class="list">
      <li class="item">Electric rate structure (flat, tiered, and time-of-use options)</li>
      <li class="item">Seasonal cooling and heating pressure on monthly bills</li>
      <li class="item">Water + sewer billing method (usage, fixed charges, or both)</li>
      <li class="item">Trash and recycling service inclusion in rent or HOA fees</li>
      <li class="item">Internet provider availability by neighborhood and address</li>
      <li class="item">Typical installation/activation fees and contract terms</li>
      <li class="item">Utility deposit requirements for new residents</li>
      <li class="item">Energy-efficiency impact from HVAC, windows, and insulation</li>
      <li class="item">Solar/net-metering availability (if owner occupied)</li>
      <li class="item">Budget billing and low-income assistance program options</li>
    </ul>

    <h2>How to Lower Utility Bills in {city_name}</h2>
    <ul class="list">
      <li class="item">Shift major electricity usage outside peak windows when TOU plans apply.</li>
      <li class="item">Use smart thermostat schedules and tune HVAC filters monthly.</li>
      <li class="item">Check for hidden leaks and install low-flow showerheads/aerators.</li>
      <li class="item">Reprice internet annually and compare bundle alternatives.</li>
      <li class="item">Ask providers about autopay, paperless, and efficiency rebate credits.</li>
    </ul>

{minnesota_detail_html}

    <h2>Explore More {city_name} and {state_name} Cost Pages</h2>
    <ul class="gridList">
      <li><a href="/utility-costs/{state_slug}/">Utility Costs in {state_name}</a></li>
      <li><a href="/utility-costs/">Utility Costs by State</a></li>
      <li><a href="/cost-of-living/{state_slug}/">Cost of Living in {state_name}</a></li>
      <li><a href="/property-taxes/{state_slug}/">Property Tax Rates in {state_name}</a></li>
      <li><a href="/services/">Home Service Cost Guides</a></li>
    </ul>

    <p><strong>Editorial note:</strong> Ranges and ratings are planning benchmarks for fast city comparison, not provider quotes.</p>
    <p><em>Last updated: {today}</em></p>
  </div>
  <script defer src="/assets/version-footer.js"></script>
</body>
</html>
"""

    if section == "property-taxes":
        profile = get_city_property_tax_profile(state_slug, city_name)
        canonical = f"{SITE_URL}/{section}/{state_slug}/{city_slug}/"
        title = f"{city_name}, {state_name} Property Tax Rates (Census ACS) | {SITE_NAME}"
        desc = (
            f"Property tax estimates for {city_name}, {state_name} from U.S. Census ACS data, "
            "including median annual property tax, home value, and effective rate."
        )
        stats_html = "<p>City-level ACS property tax data is not currently available for this place. Check back after the next data refresh.</p>"
        if profile and profile.get("median_property_tax_usd") and profile.get("median_home_value_usd"):
            med_tax = profile["median_property_tax_usd"]
            med_home = profile["median_home_value_usd"]
            med_income = profile.get("median_household_income_usd")
            eff_rate = profile.get("effective_property_tax_rate_pct")
            monthly_tax = round(med_tax / 12, 2)
            tax_to_income_pct = round((med_tax / med_income) * 100, 2) if med_income else None
            tax_on_300k = round((eff_rate / 100) * 300000, 2) if eff_rate else None
            stats_html = f"""
    <h2>Property Tax Snapshot ({city_name})</h2>
    <table>
      <thead>
        <tr><th>Metric</th><th>Value</th><th>Why it matters</th></tr>
      </thead>
      <tbody>
        <tr><td>Median annual property tax paid</td><td>${med_tax:,.0f}</td><td>Annual homeowner tax burden benchmark</td></tr>
        <tr><td>Median owner-occupied home value</td><td>${med_home:,.0f}</td><td>Used to estimate effective property tax rate</td></tr>
        <tr><td>Estimated effective property tax rate</td><td>{eff_rate:.3f}%</td><td>Normalizes tax load across home values</td></tr>
        <tr><td>Estimated monthly property tax carry</td><td>${monthly_tax:,.2f}</td><td>Useful for monthly escrow planning</td></tr>
        <tr><td>Estimated annual tax on $300,000 home</td><td>${tax_on_300k:,.2f}</td><td>Quick “any-home-value” scenario planning</td></tr>
        <tr><td>Median household income</td><td>{f'${med_income:,.0f}' if med_income else 'Not available'}</td><td>Context for affordability and burden</td></tr>
        <tr><td>Property tax as share of median income</td><td>{f'{tax_to_income_pct:.2f}%' if tax_to_income_pct is not None else 'Not available'}</td><td>Another tax-rate-style burden indicator</td></tr>
      </tbody>
    </table>
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
    <h1>{city_name}, {state_name} Property Tax Rates</h1>
    <p class="lede">City-level property tax benchmarks built from U.S. Census ACS data for quick homeowner comparison.</p>
{stats_html}
    <h2>Methodology</h2>
    <ul class="list">
      <li class="item">Primary source: U.S. Census Bureau, ACS 5-year ({ACS_DATASET.split('/')[0]}) detailed tables for places.</li>
      <li class="item">Effective property tax rate = median annual real estate taxes ÷ median owner-occupied home value.</li>
      <li class="item">These are benchmark medians, not parcel-level assessor tax bills.</li>
    </ul>
    <h2>More tax pages</h2>
    <ul class="gridList">
      <li><a href="/property-taxes/{state_slug}/">Property Taxes in {state_name}</a></li>
      <li><a href="/property-taxes/">Property Taxes by State</a></li>
      <li><a href="/cost-of-living/{state_slug}/">Cost of Living in {state_name}</a></li>
    </ul>
    <p><em>Last updated: {today}</em></p>
  </div>
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


def refresh_existing_property_tax_pages(state_slug_filter: str | None = None) -> int:
    refreshed = 0
    for path in Path("property-taxes").glob("*/*/index.html"):
        state_slug = path.parts[1]
        city_slug = path.parts[2]
        if state_slug_filter and state_slug != state_slug_filter:
            continue
        if city_slug.endswith(("-county", "-parish", "-borough", "-census-area")):
            continue
        city_name = city_slug.replace("-", " ").title()
        path.write_text(city_page_html("property-taxes", state_slug, city_name), encoding="utf-8")
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
    city_options = "\n".join(
        f'<option value="/{section}/{state_slug}/{slugify(c)}/">{escape(c)}</option>' for c in cities
    ) if cities else ""
    lis = "\n".join(
        f'<li><a class="cityLink" href="/{section}/{state_slug}/{slugify(c)}/">{escape(c)}</a></li>' for c in cities
    ) if cities else '<li>No city pages are published for this state yet.</li>'
    section_title = SECTION_META[section]["title"]
    section_links = "\n".join(
        f'<a class="pill" href="/{other_section}/{state_slug}/">{SECTION_META[other_section]["title"]}</a>'
        for other_section in SECTIONS
    )

    block = f"""<!-- POPULAR_CITIES:START -->
<div class="card">
<h2 class="sectionTitle">{state_name} insights dashboard</h2>
<p>Jump between insight pages for {state_name} and choose a city to open local detail pages.</p>
<div class="navlinks">
{section_links}
</div>
<label for="{section}-{state_slug}-city-selector"><strong>City selector ({section_title})</strong></label>
<select
  id="{section}-{state_slug}-city-selector"
  style="display:block;width:100%;max-width:420px;margin:.5rem 0 1rem;padding:.55rem;border-radius:10px;border:1px solid #d5dfeb;background:#fff;"
  onchange="if(this.value) window.location.href=this.value;"
>
  <option value="">Choose a city page...</option>
{city_options}
</select>
</div>
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
    ap.add_argument(
        "--refresh-property-tax-pages",
        action="store_true",
        help="Rewrite all existing /property-taxes/<state>/<city>/ pages with Census ACS-powered tax data.",
    )
    args = ap.parse_args()

    if args.refresh_utility_city_pages:
        state_filter = slugify(args.state) if args.state else None
        refreshed = refresh_existing_utility_city_pages(state_filter)
        print(f"Refreshed utility city pages: {refreshed}.")
        return
    if args.refresh_property_tax_pages:
        state_filter = slugify(args.state) if args.state else None
        refreshed = refresh_existing_property_tax_pages(state_filter)
        print(f"Refreshed property tax city pages: {refreshed}.")
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
