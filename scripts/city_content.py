#!/usr/bin/env python3
"""Shared city/state content helpers.

This module keeps state index pages in sync with the cities that actually
exist on disk and creates a starter JSON data file for each city page.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

SITE_NAME = "DataByArea"
SITE_URL = "https://databyarea.com"
CSS_PATH = "/assets/styles.css"
CITY_DATA_ROOT = Path("data/city-data")


US_STATES = {
    "alabama": "Alabama", "alaska": "Alaska", "arizona": "Arizona", "arkansas": "Arkansas", "california": "California",
    "colorado": "Colorado", "connecticut": "Connecticut", "delaware": "Delaware", "florida": "Florida", "georgia": "Georgia",
    "hawaii": "Hawaii", "idaho": "Idaho", "illinois": "Illinois", "indiana": "Indiana", "iowa": "Iowa", "kansas": "Kansas",
    "kentucky": "Kentucky", "louisiana": "Louisiana", "maine": "Maine", "maryland": "Maryland", "massachusetts": "Massachusetts",
    "michigan": "Michigan", "minnesota": "Minnesota", "mississippi": "Mississippi", "missouri": "Missouri", "montana": "Montana",
    "nebraska": "Nebraska", "nevada": "Nevada", "new-hampshire": "New Hampshire", "new-jersey": "New Jersey", "new-mexico": "New Mexico",
    "new-york": "New York", "north-carolina": "North Carolina", "north-dakota": "North Dakota", "ohio": "Ohio", "oklahoma": "Oklahoma",
    "oregon": "Oregon", "pennsylvania": "Pennsylvania", "rhode-island": "Rhode Island", "south-carolina": "South Carolina",
    "south-dakota": "South Dakota", "tennessee": "Tennessee", "texas": "Texas", "utah": "Utah", "vermont": "Vermont",
    "virginia": "Virginia", "washington": "Washington", "west-virginia": "West Virginia", "wisconsin": "Wisconsin", "wyoming": "Wyoming",
}


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = s.replace(".", "")
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s


def slug_to_city_name(city_slug: str) -> str:
    return city_slug.replace("-", " ").title()


def discover_city_slugs(section: str, state_slug: str) -> list[str]:
    state_dir = Path(section) / state_slug
    if not state_dir.exists():
        return []

    city_slugs: list[str] = []
    for child in sorted(state_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name == "assets":
            continue
        city_index = child / "index.html"
        if city_index.exists():
            city_slugs.append(child.name)
    return city_slugs


def city_data_template(section: str, state_slug: str, city_slug: str, city_name: str | None = None) -> dict:
    city_label = city_name or slug_to_city_name(city_slug)
    return {
        "city_slug": city_slug,
        "city_name": city_label,
        "state_slug": state_slug,
        "state_name": US_STATES.get(state_slug, state_slug.replace("-", " ").title()),
        "section": section,
        "canonical_url": f"{SITE_URL}/{section}/{state_slug}/{city_slug}/",
        "last_seeded_utc": datetime.utcnow().isoformat() + "Z",
        "data": {
            "cost_index": None,
            "median_home_price": None,
            "median_rent": None,
            "utility_monthly": {
                "electric": None,
                "water": None,
                "gas": None,
                "internet": None,
            },
            "tax_rates": {
                "property_tax_effective_rate": None,
                "sales_tax_rate": None,
            },
            "insurance": {
                "home": None,
                "auto": None,
                "health": None,
            },
            "sources": [],
        },
    }


def ensure_city_data_seed(section: str, state_slug: str, city_slug: str, city_name: str | None = None) -> bool:
    out_dir = CITY_DATA_ROOT / section / state_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{city_slug}.json"
    if out_file.exists():
        return False
    payload = city_data_template(section, state_slug, city_slug, city_name)
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def render_state_index_html(section: str, state_slug: str, city_slugs: list[str]) -> str:
    state_name = US_STATES[state_slug]
    section_title = section.replace("-", " ").title()
    canonical = f"{SITE_URL}/{section}/{state_slug}/"
    desc = f"{section_title} in {state_name}. Compare costs by state and major cities."
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if city_slugs:
        city_items = "\n".join(
            f'      <li><a href="/{section}/{state_slug}/{city_slug}/">{slug_to_city_name(city_slug)}</a></li>'
            for city_slug in city_slugs[:200]
        )
        city_block = (
            f"    <h2>Cities in {state_name}</h2>\n"
            f"    <ul class=\"gridList\">\n{city_items}\n    </ul>"
        )
    else:
        city_block = f"    <p>No city pages are published yet for {state_name}.</p>"

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
    <h1>{section_title} in {state_name}</h1>
    <p class=\"lede\">{desc}</p>
    <ul class=\"gridList\">
      <li><a href=\"/{section}/\">Back to {section_title} by State</a></li>
      <li><a href=\"/\">DataByArea Home</a></li>
    </ul>
{city_block}
    <p><em>Last updated: {today}</em></p>
  </div>
</body>
</html>
"""
