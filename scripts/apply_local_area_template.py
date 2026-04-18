"""Batch-apply the localized utility city template to all city pages.

Usage:
  python3 scripts/apply_local_area_template.py
  python3 scripts/apply_local_area_template.py --state minnesota
"""

import argparse

from publish_popular_cities_daily import refresh_existing_utility_city_pages


def main() -> None:
    ap = argparse.ArgumentParser(description="Rewrite utility city pages using the localized layout template.")
    ap.add_argument("--state", default=None, help="Optional state slug filter, e.g. minnesota")
    args = ap.parse_args()

    refreshed = refresh_existing_utility_city_pages(args.state)
    scope = args.state or "all states"
    print(f"Localized template applied to {refreshed} utility city page(s) for {scope}.")


if __name__ == "__main__":
    main()
