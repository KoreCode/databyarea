"""API-backed data enrichment for high-intent service guide pages.

The generator uses this module to collect local market signals, normalize them,
and apply a conservative adjustment to the base project ranges. API failures are
reported as source notes instead of breaking page generation.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

try:
    from env_loader import load_local_env
except ImportError:  # pragma: no cover - package import fallback
    from scripts.env_loader import load_local_env

load_local_env(ROOT)

STATE_FIPS = {
    "alabama": "01", "alaska": "02", "arizona": "04", "arkansas": "05", "california": "06",
    "colorado": "08", "connecticut": "09", "delaware": "10", "florida": "12", "georgia": "13",
    "hawaii": "15", "idaho": "16", "illinois": "17", "indiana": "18", "iowa": "19",
    "kansas": "20", "kentucky": "21", "louisiana": "22", "maine": "23", "maryland": "24",
    "massachusetts": "25", "michigan": "26", "minnesota": "27", "mississippi": "28",
    "missouri": "29", "montana": "30", "nebraska": "31", "nevada": "32",
    "new-hampshire": "33", "new-jersey": "34", "new-mexico": "35", "new-york": "36",
    "north-carolina": "37", "north-dakota": "38", "ohio": "39", "oklahoma": "40",
    "oregon": "41", "pennsylvania": "42", "rhode-island": "44", "south-carolina": "45",
    "south-dakota": "46", "tennessee": "47", "texas": "48", "utah": "49",
    "vermont": "50", "virginia": "51", "washington": "53", "west-virginia": "54",
    "wisconsin": "55", "wyoming": "56",
}

API_KEYS = {
    "census": os.getenv("CENSUS_API_KEY", "").strip(),
    "bls": os.getenv("BLS_API_KEY", "").strip(),
    "fred": os.getenv("FRED_API_KEY", "").strip(),
    "bea": os.getenv("BEA_API_KEY", "").strip(),
    "eia": os.getenv("EIA_API_KEY", "").strip(),
    "data_gov": os.getenv("DATA_GOV_API_KEY", "").strip(),
}


@dataclass
class SourceNote:
    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def _to_float(value: Any) -> float | None:
    if value in (None, "", "null", "-666666666", "-999999999"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _money(value: float | None) -> str:
    if value is None:
        return "Not available"
    return f"${value:,.0f}"


def _number(value: float | None) -> str:
    if value is None:
        return "Not available"
    return f"{value:,.0f}"


def _percent(value: float | None) -> str:
    if value is None:
        return "Not available"
    return f"{value:.1f}%"


def _bounded(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _http_json(url: str, timeout: int, *, data: dict[str, Any] | None = None) -> Any:
    body = None
    headers = {"User-Agent": "DataByArea service-guide-generator/1.0"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _clean_source_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return "network unavailable"
    return exc.__class__.__name__


def _parse_currency_range(raw: str) -> tuple[float, float] | None:
    values = [float(item.replace(",", "")) for item in re.findall(r"\$?([0-9][0-9,]*(?:\.\d+)?)", raw)]
    if len(values) < 2:
        return None
    return values[0], values[1]


def _format_range(low: float, high: float) -> str:
    step = 25 if high < 1000 else 100
    rounded_low = round(low / step) * step
    rounded_high = round(high / step) * step
    if rounded_high <= rounded_low:
        rounded_high = rounded_low + step
    return f"${rounded_low:,.0f}-${rounded_high:,.0f}"


def _census_rows_to_dict(rows: Any) -> list[dict[str, str]]:
    if not isinstance(rows, list) or len(rows) < 2:
        return []
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:]]


def fetch_census_market(state_slug: str, state_name: str, city_name: str, timeout: int) -> tuple[dict[str, Any], SourceNote]:
    if not API_KEYS["census"]:
        return {}, SourceNote("Census ACS", "missing_key", "CENSUS_API_KEY is not configured.")
    fips = STATE_FIPS.get(state_slug)
    if not fips:
        return {}, SourceNote("Census ACS", "skipped", f"State FIPS not mapped for {state_name}.")

    params = {
        "get": "NAME,B01003_001E,B19013_001E,B25077_001E,B25064_001E",
        "for": "place:*" if city_name else f"state:{fips}",
        "key": API_KEYS["census"],
    }
    if city_name:
        params["in"] = f"state:{fips}"
    url = "https://api.census.gov/data/2023/acs/acs5?" + urllib.parse.urlencode(params)
    try:
        rows = _census_rows_to_dict(_http_json(url, timeout))
    except Exception as exc:
        return {}, SourceNote("Census ACS", "error", f"Could not refresh ACS local market data: {_clean_source_error(exc)}.")

    selected = None
    if city_name:
        wanted = city_name.lower().replace(" city", "")
        for row in rows:
            name = row.get("NAME", "").lower()
            if wanted in name and state_name.lower() in name:
                selected = row
                break
    elif rows:
        selected = rows[0]
    if not selected:
        return {}, SourceNote("Census ACS", "no_match", f"No ACS place row matched {city_name}, {state_name}.")

    data = {
        "population": _to_float(selected.get("B01003_001E")),
        "median_household_income": _to_float(selected.get("B19013_001E")),
        "median_home_value": _to_float(selected.get("B25077_001E")),
        "median_gross_rent": _to_float(selected.get("B25064_001E")),
        "place_name": selected.get("NAME", ""),
    }
    return data, SourceNote("Census ACS", "ok", "Used 2023 ACS 5-year population, income, home value, and rent fields.")


def fetch_fred_signals(timeout: int) -> tuple[dict[str, Any], SourceNote]:
    if not API_KEYS["fred"]:
        return {}, SourceNote("FRED", "missing_key", "FRED_API_KEY is not configured.")
    signals: dict[str, Any] = {}
    series = {
        "consumer_price_index": "CPIAUCSL",
        "producer_price_index": "PPIACO",
    }
    try:
        for key, series_id in series.items():
            params = {
                "series_id": series_id,
                "api_key": API_KEYS["fred"],
                "file_type": "json",
                "sort_order": "desc",
                "limit": "1",
            }
            url = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(params)
            payload = _http_json(url, timeout)
            obs = (payload.get("observations") or [{}])[0]
            signals[key] = _to_float(obs.get("value"))
            signals[f"{key}_date"] = obs.get("date")
    except Exception as exc:
        return signals, SourceNote("FRED", "error", f"Could not refresh inflation/material signals: {_clean_source_error(exc)}.")
    return signals, SourceNote("FRED", "ok", "Used latest CPI and producer price index observations for national cost pressure.")


def fetch_bls_signals(timeout: int) -> tuple[dict[str, Any], SourceNote]:
    if not API_KEYS["bls"]:
        return {}, SourceNote("BLS", "missing_key", "BLS_API_KEY is not configured.")
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    request = {
        "seriesid": ["CES2000000003"],
        "latest": "true",
        "registrationkey": API_KEYS["bls"],
    }
    try:
        payload = _http_json(url, timeout, data=request)
        series = payload.get("Results", {}).get("series", [])
        latest = (series[0].get("data") or [{}])[0] if series else {}
        value = _to_float(latest.get("value"))
    except Exception as exc:
        return {}, SourceNote("BLS", "error", f"Could not refresh construction wage signal: {_clean_source_error(exc)}.")
    return {
        "construction_avg_hourly_earnings": value,
        "construction_avg_hourly_earnings_period": f"{latest.get('periodName', '')} {latest.get('year', '')}".strip(),
    }, SourceNote("BLS", "ok", "Used latest construction average hourly earnings series as a labor-cost pressure signal.")


def fetch_bea_signals(timeout: int) -> tuple[dict[str, Any], SourceNote]:
    if not API_KEYS["bea"]:
        return {}, SourceNote("BEA", "missing_key", "BEA_API_KEY is not configured.")
    params = {
        "UserID": API_KEYS["bea"],
        "method": "GETDATASETLIST",
        "ResultFormat": "JSON",
    }
    url = "https://apps.bea.gov/api/data?" + urllib.parse.urlencode(params)
    try:
        payload = _http_json(url, timeout)
        datasets = payload.get("BEAAPI", {}).get("Results", {}).get("Dataset", [])
        available = any(item.get("DatasetName") == "Regional" for item in datasets)
    except Exception as exc:
        return {}, SourceNote("BEA", "error", f"Could not validate BEA regional dataset availability: {_clean_source_error(exc)}.")
    return {"regional_dataset_available": available}, SourceNote("BEA", "ok", "Validated BEA regional dataset availability for future income and GDP extensions.")


def estimate_adjusted_range(base_range: str, signals: dict[str, Any]) -> tuple[str, list[str], str]:
    parsed = _parse_currency_range(base_range)
    if not parsed:
        return base_range, ["Base project range kept because the source range could not be parsed."], "Template base range"

    low, high = parsed
    factors: list[tuple[str, float]] = []
    income = _to_float(signals.get("median_household_income"))
    home_value = _to_float(signals.get("median_home_value"))
    wage = _to_float(signals.get("construction_avg_hourly_earnings"))
    cpi = _to_float(signals.get("consumer_price_index"))
    ppi = _to_float(signals.get("producer_price_index"))

    if income:
        factors.append(("local income", _bounded(income / 75000, 0.88, 1.18)))
    if home_value:
        factors.append(("home value", _bounded(home_value / 325000, 0.90, 1.16)))
    if wage:
        factors.append(("construction wages", _bounded(wage / 37, 0.90, 1.22)))
    if cpi:
        factors.append(("consumer inflation", _bounded(cpi / 315, 0.94, 1.10)))
    if ppi:
        factors.append(("producer/material prices", _bounded(ppi / 260, 0.92, 1.12)))

    if not factors:
        return base_range, ["No live API cost signals were available, so the base project range is shown unchanged."], "Template base range"

    factor = sum(value for _, value in factors) / len(factors)
    adjusted = _format_range(low * factor, high * factor)
    notes = [f"Applied {name} factor {value:.2f}." for name, value in factors]
    return adjusted, notes, f"API adjusted factor {factor:.2f}"


def build_service_guide_context(
    *,
    service_slug: str,
    service_label: str,
    project_label: str,
    project_range: str,
    state_slug: str,
    state_name: str,
    city_name: str,
    timeout: int = 8,
    use_api: bool = True,
) -> dict[str, Any]:
    source_notes: list[SourceNote] = []
    signals: dict[str, Any] = {}

    if use_api:
        census_data, census_note = fetch_census_market(state_slug, state_name, city_name, timeout)
        signals.update(census_data)
        source_notes.append(census_note)
        for fetcher in (fetch_bls_signals, fetch_fred_signals, fetch_bea_signals):
            data, note = fetcher(timeout)
            signals.update(data)
            source_notes.append(note)
    else:
        source_notes.append(SourceNote("API refresh", "skipped", "Generation ran with --skip-api, so the page uses template ranges and explicit fallback notes."))

    adjusted_range, model_notes, model_label = estimate_adjusted_range(project_range, signals)
    ok_sources = sum(1 for note in source_notes if note.status == "ok")
    data_quality = "API enriched" if ok_sources >= 2 else ("Partially enriched" if ok_sources == 1 else "Template fallback")

    market_items = [
        ("Population", _number(_to_float(signals.get("population")))),
        ("Median household income", _money(_to_float(signals.get("median_household_income")))),
        ("Median home value", _money(_to_float(signals.get("median_home_value")))),
        ("Median gross rent", _money(_to_float(signals.get("median_gross_rent")))),
        ("Construction hourly earnings", _money(_to_float(signals.get("construction_avg_hourly_earnings")))),
        ("Consumer price index", f"{_to_float(signals.get('consumer_price_index')):.1f}" if _to_float(signals.get("consumer_price_index")) is not None else "Not available"),
    ]
    source_dicts = [note.as_dict() for note in source_notes]

    return {
        "service_slug": service_slug,
        "service_label": service_label,
        "project_label": project_label,
        "base_project_range": project_range,
        "adjusted_project_range": adjusted_range,
        "data_quality_label": data_quality,
        "model_label": model_label,
        "model_notes": model_notes,
        "market_items": market_items,
        "source_notes": source_dicts,
        "updated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "estimate_summary": (
            f"The {project_label} range starts from the DataByArea service template and is adjusted "
            f"with available public labor, inflation, and local market signals for {city_name or state_name}."
        ),
    }
