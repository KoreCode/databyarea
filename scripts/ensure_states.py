#!/usr/bin/env python3
"""Ensure all 50 state index pages exist for core sections.

This helps SEO coverage by guaranteeing crawlable state-level hubs.
"""

from __future__ import annotations

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


def main() -> None:
    created = 0
    updated = 0
    unchanged = 0

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
