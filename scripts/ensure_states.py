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


def state_index_html(section: str, state_slug: str) -> str:
    state_name = US_STATES[state_slug]
    section_title = section.replace("-", " ").title()
    canonical = f"{SITE_URL}/{section}/{state_slug}/"
    desc = f"{section_title} in {state_name}. Compare costs by state and major cities."
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{section_title} in {state_name} | {SITE_NAME}</title>
  <meta name=\"description\" content=\"{desc}\">
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
    <p><em>Last updated: {today}</em></p>
  </div>
</body>
</html>
"""


def main() -> None:
    created = 0
    existing = 0

    for section in SECTIONS:
        for state_slug in sorted(US_STATES):
            folder = Path(section) / state_slug
            folder.mkdir(parents=True, exist_ok=True)
            index_path = folder / "index.html"
            if index_path.exists():
                existing += 1
                continue
            index_path.write_text(state_index_html(section, state_slug), encoding="utf-8")
            created += 1
            print(f"Created: /{section}/{state_slug}/")

    print(f"State coverage check complete. Created {created}, existing {existing}.")


if __name__ == "__main__":
    main()
