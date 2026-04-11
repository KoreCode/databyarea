#!/usr/bin/env python3
"""Backfill city data JSON files for existing city pages."""

from __future__ import annotations

from pathlib import Path

from city_content import US_STATES, ensure_city_data_seed

SECTIONS = [
    "cost-of-living",
    "utility-costs",
    "property-taxes",
    "insurance-costs",
]


def main() -> None:
    seeded = 0
    for section in SECTIONS:
        for state_slug in US_STATES:
            state_dir = Path(section) / state_slug
            if not state_dir.exists():
                continue
            for child in state_dir.iterdir():
                if not child.is_dir():
                    continue
                city_index = child / "index.html"
                if not city_index.exists():
                    continue
                if ensure_city_data_seed(section, state_slug, child.name):
                    seeded += 1
    print(f"Seeded city data files: {seeded}")


if __name__ == "__main__":
    main()
