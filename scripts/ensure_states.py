#!/usr/bin/env python3
"""Ensure all 50 state index pages exist for core sections.

This helps SEO coverage by guaranteeing crawlable state-level hubs.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

SITE_NAME = "DataByArea"
SITE_URL = "https://databyarea.com"
CSS_PATH = "/assets/styles.css"

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

STATE_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new-hampshire": "NH", "new-jersey": "NJ", "new-mexico": "NM",
    "new-york": "NY", "north-carolina": "NC", "north-dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode-island": "RI", "south-carolina": "SC",
    "south-dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west-virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
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

FEATURED_COUNTIES = [
    "Los Angeles County, CA",
    "Cook County, IL",
    "Harris County, TX",
    "Maricopa County, AZ",
    "King County, WA",
    "Miami-Dade County, FL",
    "Clark County, NV",
    "Wayne County, MI",
    "Travis County, TX",
    "Salt Lake County, UT",
    "Wake County, NC",
    "Allegheny County, PA",
]

FEATURED_CITIES = [
    "New York, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    "Houston, TX",
    "Phoenix, AZ",
    "Philadelphia, PA",
    "San Antonio, TX",
    "San Diego, CA",
    "Dallas, TX",
    "Austin, TX",
    "Jacksonville, FL",
    "Columbus, OH",
]


def state_index_html(section: str, state_slug: str) -> str:
    state_name = US_STATES[state_slug]
    section_meta = SECTION_META[section]
    section_title = section_meta["title"]
    canonical = f"{SITE_URL}/{section}/{state_slug}/"
    desc = (
        f"Explore {section_title.lower()} in {state_name}. "
        f"Compare state averages and city-level differences."
    )
    today = datetime.utcnow().strftime("%Y-%m-%d")
    related_links = []
    for other_section in SECTIONS:
        if other_section == section:
            continue
        other_title = SECTION_META[other_section]["title"]
        related_links.append(
            f'<li><a href="/{other_section}/{state_slug}/">{other_title} in {state_name}</a></li>'
        )
    related_html = "\n".join(related_links)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{section_title} in {state_name} | {SITE_NAME}</title>
  <meta name=\"description\" content=\"{desc}\">
  <meta name=\"robots\" content=\"index,follow,max-image-preview:large\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <link rel=\"canonical\" href=\"{canonical}\">
  <link rel=\"stylesheet\" href=\"{CSS_PATH}\">
</head>
<body>
  <div class=\"container\">
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

    <!-- COUNTY_PAGES:ANCHOR -->
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

def section_index_html(section: str) -> str:
    section_meta = SECTION_META[section]
    section_title = section_meta["title"]
    canonical = f"{SITE_URL}/{section}/"
    desc = (
        f"Browse {section_title.lower()} estimates across all 50 U.S. states. "
        f"Use quick search plus cross-category links for complete comparisons."
    )
    state_items = "\n".join(
        f'<li class="item"><a href="/{section}/{slug}/">{name}</a></li>'
        for slug, name in sorted(US_STATES.items(), key=lambda x: x[1])
    )
    state_column_items = "\n".join(
        f'<li><a href="/{section}/{slug}/">{name}</a></li>'
        for slug, name in sorted(US_STATES.items(), key=lambda x: x[1])
    )
    county_items = "\n".join(f"<li>{county}</li>" for county in FEATURED_COUNTIES)
    city_items = "\n".join(f"<li>{city}</li>" for city in FEATURED_CITIES)
    related_sections = "\n".join(
        f'<li class="item"><a href="/{other}/">{SECTION_META[other]["title"]}</a></li>'
        for other in SECTIONS if other != section
    )
    state_url_by_abbr = ",".join(
        f'"{abbr}":"/{section}/{slug}/"'
        for slug, abbr in sorted(STATE_ABBR.items(), key=lambda x: US_STATES[x[0]])
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{section_title} by State | Data By Area</title>
  <meta name="description" content="{desc}" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="{CSS_PATH}" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/jsvectormap@1.7.0/dist/css/jsvectormap.min.css" />
  <link rel="canonical" href="{canonical}" />
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
      <h1>{section_title} by State</h1>
      <p>{desc}</p>
      <div class="breadcrumbs"><a href="/">Home</a> › <span>{section_title}</span></div>
      <div class="badges">
        <span class="badge"><span class="dot"></span> 50 states</span>
        <span class="badge">Mobile friendly</span>
        <span class="badge">Desktop friendly</span>
      </div>
      <div class="searchRow">
        <input id="q" class="input" placeholder="Search a state (e.g., Minnesota)..." />
      </div>
    </div>

    <div class="card compactTop">
      <h2 class="sectionTitle">Pick a location: state → county → city</h2>
      <p>Start with your state, then use county and city examples to refine comparisons and planning.</p>
      <div class="selectionGrid">
        <div class="interactiveMapCard">
          <h3>Select a state on the map</h3>
          <p class="mutedSmall">Click or tap any state to jump straight to its {section_title.lower()} page.</p>
          <div id="state-map" class="stateMap" aria-label="Interactive map of the United States"></div>
        </div>
        <div class="selectionColumns">
          <div class="card">
            <h3>States</h3>
            <ul class="listColumns">
              {state_column_items}
            </ul>
          </div>
          <div class="card">
            <h3>Popular counties</h3>
            <ul class="listColumns">
              {county_items}
            </ul>
            <p class="mutedSmall">County-level detail varies by dataset and update cycle.</p>
          </div>
          <div class="card">
            <h3>Popular cities</h3>
            <ul class="listColumns">
              {city_items}
            </ul>
            <p class="mutedSmall">City pages help benchmark local differences inside each state.</p>
          </div>
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>Included data & tools</h2>
        <p>Quickly compare by state, then drill into county and city-level pages where available.</p>
        <ul class="list">
          <li class="item">{section_meta["summary"].capitalize()}</li>
          <li class="item">State-by-state pages with related category links</li>
          <li class="item">Crawlable links for every U.S. state</li>
          <li class="item">User-friendly navigation designed for mobile and desktop</li>
        </ul>
      </div>
      <div class="card">
        <h2>Related categories</h2>
        <p>Use matching pages to understand total cost pressure in the same location.</p>
        <ul class="list">
          {related_sections}
        </ul>
      </div>
    </div>

    <h2 class="sectionTitle">Browse states</h2>
    <ul id="list" class="list">
      {state_items}
    </ul>

    <div class="footer">
      <p><strong>Disclaimer:</strong> Informational estimates only. Costs and rates vary by household, provider, and local area.</p>
      <p><a href="/about/">About</a> · <a href="/privacy/">Privacy Policy</a> · <a href="/contact/">Contact</a></p>
      <p>© <span id="y"></span> DataByArea.com</p>
    </div>
    <script>document.getElementById("y").textContent = new Date().getFullYear();</script>
  </div>

  <script>
    const q = document.getElementById('q');
    const items = Array.from(document.querySelectorAll('#list .item'));
    function filter(){{
      const term = q.value.trim().toLowerCase();
      items.forEach(li => {{
        const text = li.textContent.toLowerCase();
        li.style.display = text.includes(term) ? '' : 'none';
      }});
    }}
    q.addEventListener('input', filter);
  </script>
  <script src="https://cdn.jsdelivr.net/npm/jsvectormap@1.7.0/dist/js/jsvectormap.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/jsvectormap@1.7.0/dist/maps/us-merc-en.js"></script>
  <script>
    const stateUrlByAbbr = {{{state_url_by_abbr}}};
    new jsVectorMap({{
      selector: '#state-map',
      map: 'us_merc_en',
      zoomButtons: true,
      selectedRegions: [],
      onRegionTooltipShow(event, tooltip, code) {{
        const abbr = code.split('-')[1];
        if (!abbr || !stateUrlByAbbr[abbr]) {{
          return;
        }}
        tooltip.text(`${{tooltip.text()}} — View details`);
      }},
      onRegionClick(event, code) {{
        const abbr = code.split('-')[1];
        const target = stateUrlByAbbr[abbr];
        if (target) {{
          window.location.href = target;
        }}
      }},
      regionStyle: {{
        initial: {{
          fill: '#d8e7f6',
          stroke: '#7d99b5',
          strokeWidth: 1
        }},
        hover: {{
          fill: '#9ec0e2'
        }},
        selected: {{
          fill: '#4f7292'
        }}
      }}
    }});
  </script>
  <script defer src="/assets/version-footer.js"></script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate section and state index pages.")
    parser.add_argument(
        "--sections-only",
        action="store_true",
        help="Only (re)generate the 4 main category landing pages.",
    )
    args = parser.parse_args()

    created = 0
    updated = 0
    unchanged = 0

    for section in SECTIONS:
        section_dir = Path(section)
        section_dir.mkdir(parents=True, exist_ok=True)
        section_index = section_dir / "index.html"
        rendered = section_index_html(section)
        if not section_index.exists():
            section_index.write_text(rendered, encoding="utf-8")
            created += 1
            print(f"Created: /{section}/")
        else:
            current = section_index.read_text(encoding="utf-8", errors="ignore")
            if current == rendered:
                unchanged += 1
            else:
                section_index.write_text(rendered, encoding="utf-8")
                updated += 1
                print(f"Updated: /{section}/")

    if args.sections_only:
        print(f"Category template generation complete. Created {created}, updated {updated}, unchanged {unchanged}.")
        return

    for section in SECTIONS:
        for state_slug in sorted(US_STATES):
            folder = Path(section) / state_slug
            folder.mkdir(parents=True, exist_ok=True)
            index_path = folder / "index.html"
            rendered = state_index_html(section, state_slug)
            if not index_path.exists():
                index_path.write_text(rendered, encoding="utf-8")
                created += 1
                print(f"Created: /{section}/{state_slug}/")
                continue
            current = index_path.read_text(encoding="utf-8", errors="ignore")
            if current == rendered:
                unchanged += 1
                continue
            index_path.write_text(rendered, encoding="utf-8")
            updated += 1
            print(f"Updated: /{section}/{state_slug}/")

    print(f"State coverage check complete. Created {created}, updated {updated}, unchanged {unchanged}.")


if __name__ == "__main__":
    main()
