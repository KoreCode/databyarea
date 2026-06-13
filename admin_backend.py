#!/usr/bin/env python3
"""Lightweight admin backend for DataByArea automation.

Provides:
- Script catalog with descriptions and run options
- Runner settings/status
- Recent run history and latest daily summary
- API endpoint to trigger approved scripts
- Lead capture + CRM pipeline + auto-tagging + follow-up sequencing APIs

Run:
  python3 admin_backend.py
  python3 admin_backend.py --host 127.0.0.1 --port 8787
"""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import os
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from scripts.env_loader import load_local_env

REPO_ROOT = Path(__file__).resolve().parent
load_local_env(REPO_ROOT)
DAILY_LOG = REPO_ROOT / ".daily_runs.json"
CITY_LOG = REPO_ROOT / ".daily_city_runs.json"
SUMMARY_JSON = REPO_ROOT / "_deploy" / "last_daily_run_summary.json"
RUN_TIMEOUT_SECONDS = 1800
RUN_LOCK = threading.Lock()
ADMIN_ACCESS_KEY = os.getenv("ADMIN_ACCESS_KEY", "").strip()
ADMIN_KEY_PARAM = os.getenv("ADMIN_KEY_PARAM", "admin_key").strip() or "admin_key"
RATE_LIMIT_REQUESTS = int(os.getenv("ADMIN_RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("ADMIN_RATE_LIMIT_WINDOW_SECONDS", "60"))
MAX_POST_BYTES = int(os.getenv("ADMIN_MAX_POST_BYTES", "65536"))
LOG_DIR = REPO_ROOT / "_deploy" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ADMIN_LOG_PATH = LOG_DIR / "admin_backend.log"
BACKUP_DIR = REPO_ROOT / "_deploy" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
LEADS_DB = REPO_ROOT / "_deploy" / "crm_leads.json"
SERVER_STARTED_AT = time.time()
REQUEST_COUNTS: dict[str, list[float]] = {}
REQUEST_LOCK = threading.Lock()

DATA_DB = REPO_ROOT / "data" / "databyarea_local.db"
CITY_PAGE_ROOT = REPO_ROOT
DATA_DB.parent.mkdir(parents=True, exist_ok=True)

API_KEYS = {
    "census": os.getenv("CENSUS_API_KEY", "").strip(),
    "eia": os.getenv("EIA_API_KEY", "").strip(),
    "bls": os.getenv("BLS_API_KEY", "").strip(),
    "fred": os.getenv("FRED_API_KEY", "").strip(),
    "bea": os.getenv("BEA_API_KEY", "").strip(),
}

STATE_FIPS = {
    "alabama": "01", "alaska": "02", "arizona": "04", "arkansas": "05", "california": "06", "colorado": "08",
    "connecticut": "09", "delaware": "10", "district of columbia": "11", "florida": "12", "georgia": "13",
    "hawaii": "15", "idaho": "16", "illinois": "17", "indiana": "18", "iowa": "19", "kansas": "20",
    "kentucky": "21", "louisiana": "22", "maine": "23", "maryland": "24", "massachusetts": "25",
    "michigan": "26", "minnesota": "27", "mississippi": "28", "missouri": "29", "montana": "30",
    "nebraska": "31", "nevada": "32", "new hampshire": "33", "new jersey": "34", "new mexico": "35",
    "new york": "36", "north carolina": "37", "north dakota": "38", "ohio": "39", "oklahoma": "40",
    "oregon": "41", "pennsylvania": "42", "rhode island": "44", "south carolina": "45", "south dakota": "46",
    "tennessee": "47", "texas": "48", "utah": "49", "vermont": "50", "virginia": "51", "washington": "53",
    "west virginia": "54", "wisconsin": "55", "wyoming": "56",
}


def ensure_city_data_db() -> None:
    with sqlite3.connect(DATA_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS city_data (
                state_slug TEXT NOT NULL,
                city_slug TEXT NOT NULL,
                city_name TEXT NOT NULL,
                state_name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                source_json TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                PRIMARY KEY (state_slug, city_slug)
            )
            """
        )


def _http_get_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _safe_metric(fetcher, fallback: Any = None) -> Any:
    try:
        return fetcher()
    except Exception:
        return fallback


def fetch_city_metrics_from_apis(city_name: str, state_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    sources: dict[str, Any] = {}

    census = []
    if API_KEYS["census"]:
        census = _safe_metric(lambda: _http_get_json(
            f"https://api.census.gov/data/2023/acs/acs5?get=NAME,B19013_001E,B25077_001E,B25103_001E&for=place:*&in=state:*&key={API_KEYS['census']}"
        ), [])
        sources["census"] = "https://api.census.gov/data/2023/acs/acs5"

    population = None
    median_income = None
    median_home_value = None
    median_property_tax_paid = None
    if isinstance(census, list) and len(census) > 1:
        headers = census[0]
        try:
            i_name = headers.index("NAME")
            i_income = headers.index("B19013_001E")
            i_home = headers.index("B25077_001E")
            i_prop_tax = headers.index("B25103_001E") if "B25103_001E" in headers else None
            for row in census[1:]:
                name = row[i_name]
                if city_name.lower() in name.lower() and state_name.lower() in name.lower():
                    median_income = row[i_income]
                    median_home_value = row[i_home]
                    if i_prop_tax is not None:
                        median_property_tax_paid = row[i_prop_tax]
                    break
        except Exception:
            pass

    state_sales_tax_rate_pct = None
    if API_KEYS["census"]:
        state_fips = STATE_FIPS.get(state_name.lower())
        if state_fips:
            state_tax = _safe_metric(lambda: _http_get_json(
                f"https://api.census.gov/data/2023/acs/acs5?get=NAME,B08134_001E,B08134_002E&for=state:{state_fips}&key={API_KEYS['census']}"
            ), [])
            if isinstance(state_tax, list) and len(state_tax) > 1:
                head = state_tax[0]
                row = state_tax[1]
                try:
                    i_rev = head.index("B08134_001E")
                    i_tax = head.index("B08134_002E")
                    revenue = float(row[i_rev]) if row[i_rev] not in ("", None) else 0.0
                    tax = float(row[i_tax]) if row[i_tax] not in ("", None) else 0.0
                    if revenue > 0:
                        state_sales_tax_rate_pct = round((tax / revenue) * 100, 3)
                except Exception:
                    pass

    eia = {}
    if API_KEYS["eia"]:
        eia = _safe_metric(lambda: _http_get_json(
            f"https://api.eia.gov/v2/electricity/retail-sales/data/?api_key={API_KEYS['eia']}&frequency=monthly&data[0]=price&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1"
        ), {})
        sources["eia"] = "https://api.eia.gov/v2/electricity/retail-sales/data/"

    electricity_price = None
    gasoline_price_usd_per_gallon = None
    try:
        electricity_price = eia.get("response", {}).get("data", [])[0].get("price")
    except Exception:
        pass
    if API_KEYS["eia"]:
        fuel = _safe_metric(lambda: _http_get_json(
            f"https://api.eia.gov/v2/petroleum/pri/gnd/data/?api_key={API_KEYS['eia']}&frequency=weekly&data[0]=value&facets[product][]=EPMR&facets[duoarea][]=NUS&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1"
        ), {})
        if fuel:
            sources["eia_fuel"] = "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
        try:
            gasoline_price_usd_per_gallon = fuel.get("response", {}).get("data", [])[0].get("value")
        except Exception:
            pass

    bls = {}
    if API_KEYS["bls"]:
        bls = _safe_metric(lambda: _http_get_json(
            "https://api.bls.gov/publicAPI/v2/timeseries/data/LAUCN270010000000005?registrationkey=" + API_KEYS["bls"]
        ), {})
        sources["bls"] = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    unemployment_rate = None
    try:
        unemployment_rate = bls.get("Results", {}).get("series", [])[0].get("data", [])[0].get("value")
    except Exception:
        pass

    payload = {
        "city": city_name,
        "state": state_name,
        "population": population,
        "median_household_income": median_income,
        "median_home_value": median_home_value,
        "median_property_tax_paid_usd": median_property_tax_paid,
        "estimated_state_sales_tax_rate_percent": state_sales_tax_rate_pct,
        "electricity_price_cents_per_kwh": electricity_price,
        "gasoline_price_usd_per_gallon": gasoline_price_usd_per_gallon,
        "unemployment_rate": unemployment_rate,
        "refreshed_at_utc": _iso_utc(),
    }
    return payload, sources


def get_city_data(state_slug: str, city_slug: str) -> dict[str, Any] | None:
    ensure_city_data_db()
    with sqlite3.connect(DATA_DB) as conn:
        row = conn.execute("SELECT city_name,state_name,data_json,source_json,updated_at_utc FROM city_data WHERE state_slug=? AND city_slug=?", (state_slug, city_slug)).fetchone()
    if not row:
        return None
    return {
        "state_slug": state_slug, "city_slug": city_slug, "city_name": row[0], "state_name": row[1],
        "data": json.loads(row[2]), "sources": json.loads(row[3]), "updated_at_utc": row[4], "from_cache": True
    }


def upsert_city_data(state_slug: str, city_slug: str, city_name: str, state_name: str, data: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    ensure_city_data_db()
    now = _iso_utc()
    with sqlite3.connect(DATA_DB) as conn:
        conn.execute("""INSERT INTO city_data(state_slug,city_slug,city_name,state_name,data_json,source_json,updated_at_utc)
                     VALUES(?,?,?,?,?,?,?)
                     ON CONFLICT(state_slug,city_slug) DO UPDATE SET city_name=excluded.city_name,state_name=excluded.state_name,data_json=excluded.data_json,source_json=excluded.source_json,updated_at_utc=excluded.updated_at_utc""",
                     (state_slug, city_slug, city_name, state_name, json.dumps(data), json.dumps(sources), now))
    return {"state_slug": state_slug, "city_slug": city_slug, "city_name": city_name, "state_name": state_name, "data": data, "sources": sources, "updated_at_utc": now, "from_cache": False}


def city_page_html(record: dict[str, Any]) -> str:
    d = record["data"]
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{record['city_name']}, {record['state_name']} Data | DataByArea</title></head><body><h1>{record['city_name']}, {record['state_name']}</h1><p>Population: {d.get('population','N/A')}</p><p>Median household income: {d.get('median_household_income','N/A')}</p><p>Median home value: {d.get('median_home_value','N/A')}</p><p>Median property tax paid (USD): {d.get('median_property_tax_paid_usd','N/A')}</p><p>Estimated state sales tax rate (%): {d.get('estimated_state_sales_tax_rate_percent','N/A')}</p><p>Electricity price (c/kWh): {d.get('electricity_price_cents_per_kwh','N/A')}</p><p>Gasoline price (USD/gal): {d.get('gasoline_price_usd_per_gallon','N/A')}</p><p>Unemployment rate: {d.get('unemployment_rate','N/A')}</p></body></html>"""


def ensure_city_page(state_slug: str, city_slug: str) -> dict[str, Any]:
    city_name = city_slug.replace('-', ' ').title()
    state_name = state_slug.replace('-', ' ').title()
    record = get_city_data(state_slug, city_slug)
    if not record:
        data, sources = fetch_city_metrics_from_apis(city_name, state_name)
        record = upsert_city_data(state_slug, city_slug, city_name, state_name, data, sources)
    out_path = CITY_PAGE_ROOT / state_slug / city_slug / 'index.html'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(city_page_html(record), encoding='utf-8')
    return record


logger = logging.getLogger("databyarea.admin")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(ADMIN_LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

SCRIPT_CATALOG: dict[str, dict[str, Any]] = {
    "one_button_daily": {
        "path": "one_button_daily.py",
        "description": "Main daily pipeline: city publish + build + sitemap + zip + summary.",
        "safe_args": ["--cities", "--services", "--no-cities", "--relink", "--clean", "--force"],
        "value_args": ["--cities", "--services"],
        "examples": [
            ["--cities", "10"],
            ["--services", "1", "--cities", "10"],
            ["--no-cities", "--relink", "--clean"],
        ],
    },
    "publish_popular_cities": {
        "path": "publish_popular_cities_daily.py",
        "description": "Generate city pages from data/popular_cities.csv.",
        "safe_args": ["--max", "--inject", "--force", "--overwrite"],
        "value_args": ["--max"],
        "examples": [["--max", "10"], ["--max", "25", "--inject"]],
    },
    "build_site": {
        "path": "scripts/build_site.py",
        "description": "Generate service/state pages and update manifest.",
        "safe_args": [],
        "examples": [[]],
    },
    "agent_quality_review": {
        "path": "scripts/site_quality_agents.py",
        "description": "Run multi-agent quality checks and optional site generation.",
        "safe_args": ["--generate"],
        "examples": [[], ["--generate"]],
    },
    "relink": {
        "path": "relink_existing_pages.py",
        "description": "Rebuild internal links across existing pages.",
        "safe_args": [],
        "examples": [[]],
    },
    "clean_site": {
        "path": "auto_clean_site.py",
        "description": "Cleanup helper for generated site files.",
        "safe_args": [],
        "examples": [[]],
    },
    "ensure_indexes": {
        "path": "index_everywhere.py",
        "description": "Ensures every directory has an index.html file.",
        "safe_args": [],
        "examples": [[]],
    },
    "make_sitemap": {
        "path": "makesitemap.py",
        "description": "Regenerates sitemap.xml.",
        "safe_args": [],
        "examples": [[]],
    },
    "backup_snapshot": {
        "path": "scripts/backup_snapshot.py",
        "description": "Creates timestamped backup tarball of critical operational artifacts.",
        "safe_args": ["--include-site", "--retention-days"],
        "value_args": ["--retention-days"],
        "examples": [[], ["--retention-days", "14"], ["--include-site"]],
    },
    "content_distribution_workflow": {
        "path": "scripts/content_distribution_workflow.py",
        "description": "Builds content calendar, article drafts, social repurposing, and publish queue outputs.",
        "safe_args": ["--config", "--briefs", "--days", "--start-date"],
        "value_args": ["--config", "--briefs", "--days", "--start-date"],
        "examples": [[], ["--days", "14"], ["--start-date", "2026-04-22"]],
    },
    "weekly_kpi_report": {
        "path": "scripts/weekly_kpi_report.py",
        "description": "Generates weekly KPI report artifacts and optional webhook delivery payload.",
        "safe_args": ["--input", "--webhook-url", "--dry-run"],
        "value_args": ["--input", "--webhook-url"],
        "examples": [[], ["--input", "data/weekly_kpi_inputs.json"], ["--dry-run"]],
    },
}

SETTINGS = {
    "repo_root": str(REPO_ROOT),
    "logs": {
        "daily_runs": str(DAILY_LOG),
        "daily_city_runs": str(CITY_LOG),
        "latest_summary": str(SUMMARY_JSON),
    },
    "python_executable": sys.executable,
    "timezone": "UTC",
    "run_timeout_seconds": RUN_TIMEOUT_SECONDS,
    "admin_key_param": ADMIN_KEY_PARAM,
    "admin_access_key_configured": bool(ADMIN_ACCESS_KEY),
    "admin_log_path": str(ADMIN_LOG_PATH),
    "backup_directory": str(BACKUP_DIR),
    "rate_limit": {"requests": RATE_LIMIT_REQUESTS, "window_seconds": RATE_LIMIT_WINDOW_SECONDS},
    "max_post_bytes": MAX_POST_BYTES,
}
CRM_PIPELINE_STAGES = ["new", "qualified", "proposal", "negotiation", "won", "lost"]
CRM_SEQUENCE_BY_INTENT = {
    "high_intent": [
        {"offset_hours": 0, "channel": "email", "template": "instant-qualification"},
        {"offset_hours": 24, "channel": "sms", "template": "day1-checkin"},
        {"offset_hours": 72, "channel": "email", "template": "case-study-offer"},
    ],
    "default": [
        {"offset_hours": 4, "channel": "email", "template": "intro-and-next-step"},
        {"offset_hours": 48, "channel": "email", "template": "value-recap"},
        {"offset_hours": 120, "channel": "sms", "template": "final-follow-up"},
    ],
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_crm_state() -> dict[str, Any]:
    base = {"leads": []}
    loaded = load_json(LEADS_DB, base)
    if not isinstance(loaded, dict):
        return base
    leads = loaded.get("leads", [])
    if not isinstance(leads, list):
        loaded["leads"] = []
    return loaded


def _iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_high_intent(payload: dict[str, Any]) -> bool:
    text = " ".join(str(payload.get(k, "")).lower() for k in ("message", "timeline", "service", "budget"))
    high_intent_terms = ("asap", "urgent", "immediately", "this week", "quote", "ready")
    return any(term in text for term in high_intent_terms)


def _auto_tags(payload: dict[str, Any]) -> list[str]:
    tags = {"website_form"}
    for key in ("service", "location", "source"):
        value = str(payload.get(key, "")).strip().lower()
        if value:
            tags.add(f"{key}:{value.replace(' ', '-')}")
    budget = str(payload.get("budget", "")).strip().lower()
    if budget:
        if any(s in budget for s in ("5000", "10000", "premium", "high")):
            tags.add("budget:high")
        elif any(s in budget for s in ("1000", "low", "starter")):
            tags.add("budget:entry")
        else:
            tags.add("budget:mid")
    tags.add("intent:high" if _is_high_intent(payload) else "intent:nurture")
    return sorted(tags)


def _build_sequence(tags: list[str], created_at: str) -> list[dict[str, Any]]:
    created_ts = datetime.fromisoformat(created_at)
    template = CRM_SEQUENCE_BY_INTENT["high_intent" if "intent:high" in tags else "default"]
    sequence: list[dict[str, Any]] = []
    for step in template:
        due = created_ts.timestamp() + int(step["offset_hours"]) * 3600
        sequence.append(
            {
                **step,
                "status": "queued",
                "due_at_utc": datetime.fromtimestamp(due, tz=timezone.utc).isoformat(),
                "sent_at_utc": None,
            }
        )
    return sequence


def capture_lead(payload: dict[str, Any], ip: str) -> tuple[bool, dict[str, Any], int]:
    required = ("name", "email")
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        return False, {"ok": False, "error": f"Missing required fields: {', '.join(missing)}"}, 400

    state = load_crm_state()
    created_at = _iso_utc()
    tags = _auto_tags(payload)
    lead = {
        "id": f"lead_{uuid4().hex[:12]}",
        "name": str(payload.get("name", "")).strip(),
        "email": str(payload.get("email", "")).strip().lower(),
        "phone": str(payload.get("phone", "")).strip(),
        "service": str(payload.get("service", "")).strip(),
        "location": str(payload.get("location", "")).strip(),
        "source": str(payload.get("source", "web_form")).strip() or "web_form",
        "message": str(payload.get("message", "")).strip(),
        "budget": str(payload.get("budget", "")).strip(),
        "timeline": str(payload.get("timeline", "")).strip(),
        "consent": bool(payload.get("consent", True)),
        "captured_from_ip": ip,
        "created_at_utc": created_at,
        "updated_at_utc": created_at,
        "stage": "new",
        "tags": tags,
        "follow_up_sequence": _build_sequence(tags, created_at),
        "activity": [{"event": "captured", "utc": created_at, "note": "Lead captured from form"}],
    }
    state["leads"].append(lead)
    save_json(LEADS_DB, state)
    return True, {"ok": True, "lead": lead}, 201


def list_leads(stage: str = "", tag: str = "") -> dict[str, Any]:
    state = load_crm_state()
    leads = state.get("leads", [])
    if stage:
        leads = [lead for lead in leads if lead.get("stage") == stage]
    if tag:
        leads = [lead for lead in leads if tag in lead.get("tags", [])]
    leads = sorted(leads, key=lambda lead: lead.get("created_at_utc", ""), reverse=True)
    return {"ok": True, "count": len(leads), "leads": leads}


def update_lead_stage(lead_id: str, stage: str) -> tuple[bool, dict[str, Any], int]:
    if stage not in CRM_PIPELINE_STAGES:
        return False, {"ok": False, "error": f"Invalid stage '{stage}'. Allowed: {CRM_PIPELINE_STAGES}"}, 400
    state = load_crm_state()
    now = _iso_utc()
    for lead in state.get("leads", []):
        if lead.get("id") != lead_id:
            continue
        previous = lead.get("stage")
        lead["stage"] = stage
        lead["updated_at_utc"] = now
        lead.setdefault("activity", []).append({"event": "stage_changed", "utc": now, "note": f"{previous} -> {stage}"})
        save_json(LEADS_DB, state)
        return True, {"ok": True, "lead": lead}, 200
    return False, {"ok": False, "error": f"Lead not found: {lead_id}"}, 404


def advance_follow_up(lead_id: str) -> tuple[bool, dict[str, Any], int]:
    state = load_crm_state()
    now = _iso_utc()
    for lead in state.get("leads", []):
        if lead.get("id") != lead_id:
            continue
        for step in lead.get("follow_up_sequence", []):
            if step.get("status") == "queued":
                step["status"] = "sent"
                step["sent_at_utc"] = now
                lead["updated_at_utc"] = now
                lead.setdefault("activity", []).append(
                    {"event": "follow_up_sent", "utc": now, "note": f"{step.get('channel')}:{step.get('template')}"}
                )
                save_json(LEADS_DB, state)
                return True, {"ok": True, "lead": lead, "sent_step": step}, 200
        return False, {"ok": False, "error": "No queued follow-up steps remaining for this lead"}, 409
    return False, {"ok": False, "error": f"Lead not found: {lead_id}"}, 404


def _client_ip(handler: "Handler") -> str:
    forwarded = handler.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return handler.client_address[0] if handler.client_address else "unknown"


def _rate_limited(ip: str) -> tuple[bool, int]:
    now = time.time()
    floor = now - RATE_LIMIT_WINDOW_SECONDS
    with REQUEST_LOCK:
        bucket = [ts for ts in REQUEST_COUNTS.get(ip, []) if ts >= floor]
        if len(bucket) >= RATE_LIMIT_REQUESTS:
            retry_after = max(1, int(bucket[0] + RATE_LIMIT_WINDOW_SECONDS - now))
            REQUEST_COUNTS[ip] = bucket
            return True, retry_after
        bucket.append(now)
        REQUEST_COUNTS[ip] = bucket
    return False, 0


def validate_args(script_key: str, args: list[str]) -> tuple[bool, list[str], str]:
    spec = SCRIPT_CATALOG[script_key]
    allowed = set(spec.get("safe_args", []))
    value_args = set(spec.get("value_args", []))

    out: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token not in allowed:
            return False, [], f"Argument not allowed for {script_key}: {token}"
        out.append(token)
        if token in value_args:
            if i + 1 >= len(args):
                return False, [], f"Missing value for argument: {token}"
            value = args[i + 1]
            if value.startswith("--"):
                return False, [], f"Expected value after {token}, got option: {value}"
            out.append(value)
            i += 2
            continue
        i += 1

    return True, out, ""


def run_script(script_key: str, args: list[str]) -> dict[str, Any]:
    if script_key not in SCRIPT_CATALOG:
        return {"ok": False, "error": f"Unknown script key: {script_key}"}

    spec = SCRIPT_CATALOG[script_key]
    script_path = REPO_ROOT / spec["path"]
    if not script_path.exists():
        return {"ok": False, "error": f"Script not found: {script_path}"}
    ok, checked_args, err = validate_args(script_key, args)
    if not ok:
        return {"ok": False, "error": err}

    if not RUN_LOCK.acquire(blocking=False):
        return {"ok": False, "error": "Another script is currently running. Try again shortly."}

    started = time.perf_counter()
    try:
        cmd = [sys.executable, str(script_path)] + checked_args
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=RUN_TIMEOUT_SECONDS,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "cmd": cmd,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
            "ran_at_utc": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(time.perf_counter() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": f"Script timed out after {RUN_TIMEOUT_SECONDS} seconds",
            "cmd": [sys.executable, str(script_path)] + checked_args,
            "stdout": (exc.stdout or "")[-12000:],
            "stderr": (exc.stderr or "")[-12000:],
            "ran_at_utc": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(time.perf_counter() - started, 3),
        }
    finally:
        RUN_LOCK.release()


def dashboard_html() -> str:
    cards = []
    for key, spec in SCRIPT_CATALOG.items():
        examples = " • ".join(" ".join(e) if e else "(no args)" for e in spec["examples"])
        safe_args = " ".join(spec["safe_args"]) or "(none)"
        cards.append(
            f"""
            <button class="command-card" onclick="runScript('{key}')">
              <div class="command-head">
                <span class="status-dot"></span>
                <span class="command-name">{key}</span>
                <span class="chip">Run</span>
              </div>
              <p class="command-desc">{spec['description']}</p>
              <div class="command-meta"><strong>Script:</strong> <code>{spec['path']}</code></div>
              <div class="command-meta"><strong>Allowed args:</strong> <code>{safe_args}</code></div>
              <div class="command-meta"><strong>Examples:</strong> <code>{examples}</code></div>
            </button>
            """
        )

    return f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width,initial-scale=1'>
  <title>DataByArea Admin Backend</title>
  <style>
    :root {{
      --bg:#050505;
      --panel:#0a0a0a;
      --border:#1e293b80;
      --text:#e2e8f0;
      --muted:#64748b;
      --accent:#f59e0b;
      --success:#34d399;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 24px;
    }}
    .shell {{ max-width: 1280px; margin: 0 auto; }}
    .topbar {{
      display:flex; justify-content: space-between; align-items:flex-end; gap:14px;
      border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:20px;
      flex-wrap:wrap;
    }}
    h1 {{ margin:0; text-transform:uppercase; letter-spacing:-0.02em; font-size:30px; color:#fff; }}
    .version {{ color:var(--accent); font-size:11px; font-style:italic; margin-left:6px; }}
    .subtitle {{ margin-top:6px; font-size:10px; text-transform:uppercase; letter-spacing:0.2em; color:var(--muted); font-weight:700; }}
    .uptime {{
      border:1px solid var(--border); background:#0f172a70; border-radius:10px;
      padding:10px 14px; text-align:right;
    }}
    .uptime-label {{ font-size:9px; text-transform:uppercase; color:var(--muted); font-weight:700; }}
    .uptime-val {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:24px; color:var(--success); line-height:1.1; }}
    .stats {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(220px,1fr)); gap:12px; margin-bottom:20px; }}
    .stat {{
      background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:14px;
    }}
    .stat-label {{ font-size:10px; text-transform:uppercase; color:var(--muted); font-weight:700; }}
    .stat-value {{ color:#fff; font-size:26px; font-weight:900; margin-top:4px; }}
    .stat-sub {{ font-size:10px; color:#475569; margin-top:2px; }}
    .grid {{ display:grid; grid-template-columns:2fr 1fr; gap:18px; }}
    .panel {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; overflow:hidden; }}
    .panel-head {{
      padding:14px 16px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; gap:8px;
      font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:700;
    }}
    .small {{ font-size:10px; color:var(--muted); }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ padding:12px; border-bottom:1px solid #1e293b50; text-align:left; }}
    th {{ font-size:10px; text-transform:uppercase; color:var(--muted); }}
    td {{ font-size:13px; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .status {{ text-align:right; }}
    .badge {{
      display:inline-block; font-size:9px; border:1px solid #34d39950; color:var(--success);
      background:#34d39915; padding:3px 6px; border-radius:999px; text-transform:uppercase; font-weight:700;
    }}
    .commands {{ padding:10px; display:grid; gap:10px; }}
    .command-card {{
      width:100%; border:1px solid var(--border); background:#0f172a40; color:inherit; text-align:left;
      border-radius:10px; padding:12px; cursor:pointer;
    }}
    .command-card:hover {{ border-color:#334155; }}
    .command-head {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
    .status-dot {{ width:8px; height:8px; border-radius:99px; background:var(--success); }}
    .command-name {{ font-size:12px; text-transform:uppercase; font-weight:800; letter-spacing:.08em; }}
    .chip {{
      margin-left:auto; font-size:9px; text-transform:uppercase; padding:2px 8px; border-radius:999px;
      border:1px solid #f59e0b40; color:var(--accent); background:#f59e0b12; font-weight:700;
    }}
    .command-desc {{ margin:0 0 6px 0; color:#94a3b8; font-size:12px; }}
    .command-meta {{ color:#94a3b8; font-size:11px; margin-top:2px; }}
    code {{ background:#1e293b80; color:#cbd5e1; padding:2px 6px; border-radius:4px; }}
    .controls {{ padding:12px; border-top:1px solid var(--border); display:grid; gap:8px; }}
    .input {{
      width:100%; border:1px solid #334155; background:#020617; color:#e2e8f0;
      border-radius:8px; padding:8px 10px;
    }}
    .actions {{ display:flex; gap:8px; flex-wrap:wrap; }}
    .btn {{
      cursor:pointer; padding:8px 12px; border-radius:8px; border:1px solid #334155;
      background:#0f172a; color:#e2e8f0; font-size:12px; font-weight:700;
    }}
    .btn:hover {{ border-color:#475569; }}
    textarea {{
      width:100%; min-height:240px; border-radius:10px; border:1px solid var(--border); background:#020617;
      color:#cbd5e1; margin-top:14px; padding:12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12px;
    }}
    @media (max-width: 1000px) {{
      .grid {{ grid-template-columns:1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div>
        <h1>DataByArea <span class="version">Mogul Command v1.0</span></h1>
        <p class="subtitle">National Data Infrastructure // Internal System Reboot Active</p>
      </div>
      <div class="uptime">
        <div class="uptime-label">Sovereign Uptime</div>
        <div id="uptime" class="uptime-val">DAY 01</div>
      </div>
    </header>

    <section class="stats">
      <article class="stat"><div class="stat-label">System Saturation</div><div class="stat-value">0.00 ng/mL</div><div class="stat-sub">Reset from legacy load</div></article>
      <article class="stat"><div class="stat-label">Survival Probability</div><div class="stat-value">0.1%</div><div class="stat-sub">Outlier status confirmed</div></article>
      <article class="stat"><div class="stat-label">Domain Fleet</div><div id="domain-count" class="stat-value">0 Active</div><div class="stat-sub">Connected admin endpoints</div></article>
      <article class="stat"><div class="stat-label">Whitelisted Scripts</div><div id="script-count" class="stat-value">0</div><div class="stat-sub">Run-safe catalog entries</div></article>
    </section>

    <div class="grid">
      <section class="panel">
        <div class="panel-head">
          <span>Automation Pipeline Controls</span>
          <span class="small">Live Local Feed</span>
        </div>
        <div class="commands">
          {''.join(cards)}
        </div>
        <div class="controls">
          <label for="args" class="small">Optional args for selected script (space-separated):</label>
          <input id="args" class="input" placeholder="--services 1 --cities 10 --relink --clean" />
          <div class="actions">
            <button class="btn" onclick="loadOverview()">Refresh Overview</button>
            <button class="btn" onclick="runScript('one_button_daily')">Run Daily Pipeline</button>
          </div>
        </div>
      </section>

      <aside class="panel">
        <div class="panel-head">
          <span>Mission Status</span>
          <span class="small">Latest Signals</span>
        </div>
        <table>
          <thead>
            <tr><th>Module</th><th>State</th><th class="status">Status</th></tr>
          </thead>
          <tbody class="mono">
            <tr><td>Config API</td><td>/api/config</td><td class="status"><span class="badge">Synced</span></td></tr>
            <tr><td>History API</td><td>/api/history</td><td class="status"><span class="badge">Synced</span></td></tr>
            <tr><td>Summary API</td><td>/api/last-summary</td><td class="status"><span class="badge">Synced</span></td></tr>
          </tbody>
        </table>
      </aside>
    </div>

    <textarea id='out' readonly></textarea>
  </div>

<script>
const qp = new URLSearchParams(window.location.search);
const keyParam = '{ADMIN_KEY_PARAM}';
const keyValue = qp.get(keyParam);
const suffix = keyValue ? `?${{keyParam}}=${{encodeURIComponent(keyValue)}}` : '';

async function loadOverview() {{
  const [cfg, hist, summary] = await Promise.all([
    fetch('/api/config' + suffix).then(r=>r.json()),
    fetch('/api/history' + suffix).then(r=>r.json()),
    fetch('/api/last-summary' + suffix).then(r=>r.json()),
  ]);
  const scriptCount = Object.keys(cfg.scripts || {{}}).length;
  document.getElementById('script-count').textContent = String(scriptCount);
  document.getElementById('domain-count').textContent = scriptCount + ' Active';

  const now = new Date();
  const day = String(now.getUTCDate()).padStart(2, '0');
  document.getElementById('uptime').textContent = `DAY ${{day}}`;

  document.getElementById('out').value = JSON.stringify({{config: cfg, history: hist, last_summary: summary}}, null, 2);
}}

async function runScript(scriptKey) {{
  const argLine = document.getElementById('args').value.trim();
  const args = argLine ? argLine.split(/\\s+/) : [];
  const res = await fetch('/api/run' + suffix, {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{script: scriptKey, args}})
  }});
  const data = await res.json();
  document.getElementById('out').value = JSON.stringify(data, null, 2);
}}

loadOverview();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _path_parts(self):
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    def _extract_admin_key(self) -> str:
        _, query = self._path_parts()
        qv = (query.get(ADMIN_KEY_PARAM) or [""])[0]
        hv = self.headers.get("X-Admin-Key", "")
        return (hv or qv or "").strip()

    def _authorized(self) -> bool:
        # If no ADMIN_ACCESS_KEY is configured, keep current behavior open.
        if not ADMIN_ACCESS_KEY:
            return True
        provided = self._extract_admin_key()
        if not provided:
            return False
        return hmac.compare_digest(provided, ADMIN_ACCESS_KEY)

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("http %s - %s", self.address_string(), format % args)

    def _apply_security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; img-src 'self' data:;",
        )

    def _send_json(self, payload: Any, status: int = 200, extra_headers: dict[str, str] | None = None) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._apply_security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        if extra_headers:
            for header, value in extra_headers.items():
                self.send_header(header, value)
        self.end_headers()
        self.wfile.write(raw)

    def _send_html(self, html: str) -> None:
        raw = html.encode("utf-8")
        self.send_response(200)
        self._apply_security_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path, _ = self._path_parts()
        ip = _client_ip(self)
        limited, retry_after = _rate_limited(ip)
        if limited:
            self._send_json(
                {"ok": False, "error": "Rate limit exceeded"},
                status=429,
                extra_headers={"Retry-After": str(retry_after)},
            )
            return
        logger.info("GET %s ip=%s", path, ip)
        if path != "/api/health" and not self._authorized():
            self._send_json({"ok": False, "error": f"Unauthorized. Supply {ADMIN_KEY_PARAM}=... in URL or X-Admin-Key header."}, status=401)
            return

        if path == "/":
            self._send_html(dashboard_html())
            return
        if path == "/api/config":
            payload = {
                "scripts": SCRIPT_CATALOG,
                "settings": SETTINGS,
                "crm": {
                    "pipeline_stages": CRM_PIPELINE_STAGES,
                    "sequence_templates": CRM_SEQUENCE_BY_INTENT,
                    "lead_store_path": str(LEADS_DB),
                },
            }
            self._send_json(payload)
            return
        if path == "/api/health":
            uptime_seconds = int(time.time() - SERVER_STARTED_AT)
            self._send_json(
                {
                    "ok": True,
                    "utc": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": uptime_seconds,
                    "started_at_utc": datetime.fromtimestamp(SERVER_STARTED_AT, tz=timezone.utc).isoformat(),
                }
            )
            return
        if path == "/api/history":
            self._send_json(
                {
                    "daily_runs": load_json(DAILY_LOG, {}),
                    "daily_city_runs": load_json(CITY_LOG, {}),
                }
            )
            return
        if path == "/api/last-summary":
            self._send_json(load_json(SUMMARY_JSON, {"note": "No summary generated yet."}))
            return
        if path.startswith("/api/databyarea/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 4:
                _, _, state_slug, city_slug = parts
                record = get_city_data(state_slug, city_slug)
                if not record:
                    city_name = city_slug.replace("-", " ").title()
                    state_name = state_slug.replace("-", " ").title()
                    data, sources = fetch_city_metrics_from_apis(city_name, state_name)
                    record = upsert_city_data(state_slug, city_slug, city_name, state_name, data, sources)
                self._send_json({"ok": True, "record": record})
                return

        if path.startswith("/minnesota/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 2:
                _, city_slug = parts
                record = ensure_city_page("minnesota", city_slug)
                self._send_html(city_page_html(record))
                return

        if path == "/api/leads":
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            stage = (query.get("stage") or [""])[0].strip()
            tag = (query.get("tag") or [""])[0].strip()
            self._send_json(list_leads(stage=stage, tag=tag))
            return
        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        path, _ = self._path_parts()
        ip = _client_ip(self)
        limited, retry_after = _rate_limited(ip)
        if limited:
            self._send_json(
                {"ok": False, "error": "Rate limit exceeded"},
                status=429,
                extra_headers={"Retry-After": str(retry_after)},
            )
            return
        logger.info("POST %s ip=%s", path, ip)
        if not self._authorized():
            self._send_json({"ok": False, "error": f"Unauthorized. Supply {ADMIN_KEY_PARAM}=... in URL or X-Admin-Key header."}, status=401)
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_POST_BYTES:
            self._send_json({"ok": False, "error": f"Payload too large (>{MAX_POST_BYTES} bytes)"}, status=413)
            return
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "error": "Invalid JSON body"}, status=400)
            return

        if path == "/api/run":
            script_key = str(payload.get("script", "")).strip()
            args = payload.get("args", [])
            if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
                self._send_json({"ok": False, "error": "args must be a list of strings"}, status=400)
                return
            result = run_script(script_key, args)
            self._send_json(result, status=200 if result.get("ok") else 400)
            return

        if path == "/api/leads/capture":
            ok, result, status = capture_lead(payload, ip)
            self._send_json(result, status=status if not ok else 201)
            return

        if path.startswith("/api/leads/") and path.endswith("/stage"):
            lead_id = path.removeprefix("/api/leads/").removesuffix("/stage").strip("/")
            stage = str(payload.get("stage", "")).strip()
            ok, result, status = update_lead_stage(lead_id, stage)
            self._send_json(result, status=status)
            return

        if path.startswith("/api/leads/") and path.endswith("/follow-up/advance"):
            lead_id = path.removeprefix("/api/leads/").removesuffix("/follow-up/advance").strip("/")
            ok, result, status = advance_follow_up(lead_id)
            self._send_json(result, status=status)
            return

        self._send_json({"error": "Not found"}, status=404)


def main() -> None:
    parser = argparse.ArgumentParser(description="DataByArea admin backend for script operations.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    logger.info("Admin backend running at http://%s:%s", args.host, args.port)
    logger.info("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
