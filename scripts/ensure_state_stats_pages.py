#!/usr/bin/env python3
"""Generate state-level main statistics pages using the same retrieval rules as city pages."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from admin_backend import fetch_city_metrics_from_apis

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


def state_page_html(state_name: str, data: dict) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{state_name} Main Statistics | DataByArea</title></head><body>"
        f"<h1>{state_name} Main Statistics</h1>"
        f"<p>Population: {data.get('population', 'N/A')}</p>"
        f"<p>Median household income: {data.get('median_household_income', 'N/A')}</p>"
        f"<p>Median home value: {data.get('median_home_value', 'N/A')}</p>"
        f"<p>Electricity price (c/kWh): {data.get('electricity_price_cents_per_kwh', 'N/A')}</p>"
        f"<p>Unemployment rate: {data.get('unemployment_rate', 'N/A')}</p>"
        f"<p>Weather station: {data.get('weather_station', 'N/A')}</p>"
        f"<p>FEMA risk sample records: {data.get('fema_county_records_sample', 'N/A')}</p>"
        f"<p>FBI arrest sample records: {data.get('fbi_arrest_records_sample', 'N/A')}</p>"
        "</body></html>"
    )


def main() -> None:
    for state_slug, state_name in US_STATES.items():
        data, _ = fetch_city_metrics_from_apis(state_name, state_name)
        out = Path(state_slug) / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(state_page_html(state_name, data), encoding="utf-8")
        print(f"generated {out}")


if __name__ == "__main__":
    main()
