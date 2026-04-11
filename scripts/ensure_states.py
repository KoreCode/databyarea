#!/usr/bin/env python3
"""Ensure all 50 state index pages exist for core sections.

This helps SEO coverage by guaranteeing crawlable state-level hubs.
"""

from __future__ import annotations

from pathlib import Path

from city_content import (
    US_STATES,
    discover_city_slugs,
    ensure_city_data_seed,
    render_state_index_html,
)

SECTIONS = [
    "cost-of-living",
    "utility-costs",
    "property-taxes",
    "insurance-costs",
]

def main() -> None:
    created = 0
    updated = 0
    seeded = 0

    for section in SECTIONS:
        for state_slug in sorted(US_STATES):
            folder = Path(section) / state_slug
            folder.mkdir(parents=True, exist_ok=True)
            index_path = folder / "index.html"

            city_slugs = discover_city_slugs(section, state_slug)
            html = render_state_index_html(section, state_slug, city_slugs)
            if index_path.exists():
                updated += 1
            else:
                created += 1
                print(f"Created: /{section}/{state_slug}/")
            index_path.write_text(html, encoding="utf-8")

            for city_slug in city_slugs:
                if ensure_city_data_seed(section, state_slug, city_slug):
                    seeded += 1

    print(f"State coverage check complete. Created {created}, updated {updated}, seeded city datasets {seeded}.")


if __name__ == "__main__":
    main()
