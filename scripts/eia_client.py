#!/usr/bin/env python3
"""EIA API client with caching, polite request pacing, and local storage helpers."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

EIA_API_URL = "https://api.eia.gov/v2/"
DEFAULT_EIA_API_KEY = "2OKDrEV0VEb6XGdTbFfRVXzEzIdnBMbhJyTGjtog"
DEFAULT_CACHE_TTL_SECONDS = 6 * 60 * 60
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 0.35
DEFAULT_MAX_RETRIES = 3
DEFAULT_DB_PATH = Path("data/api_metrics.db")
DEFAULT_CACHE_DIR = Path("data/api_cache")

_LAST_REQUEST_TS = 0.0


class EIAClientError(RuntimeError):
    """Raised for recoverable EIA API errors."""


def resolve_api_key() -> str:
    """Resolve EIA API key from env, falling back to configured project key."""
    return os.getenv("EIA_API_KEY", DEFAULT_EIA_API_KEY).strip()


def _to_int(env_name: str, default: int) -> int:
    raw = os.getenv(env_name, str(default)).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _to_float(env_name: str, default: float) -> float:
    raw = os.getenv(env_name, str(default)).strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def _cache_key(series_id: str, start: str | None, end: str | None, length: int) -> str:
    safe_series = series_id.strip("/").replace("/", "__")
    safe_start = start or "none"
    safe_end = end or "none"
    return f"{safe_series}--{safe_start}--{safe_end}--{length}.json"


def build_series_url(series_id: str, *, start: str | None = None, end: str | None = None, length: int = 12) -> str:
    """Build a series query URL for the EIA v2 API."""
    api_key = resolve_api_key()
    if not api_key:
        raise EIAClientError("Missing EIA API key. Set EIA_API_KEY.")

    params: dict[str, Any] = {
        "api_key": api_key,
        "frequency": "monthly",
        "data[0]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": max(1, int(length)),
    }
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    series_path = series_id.strip("/")
    return f"{EIA_API_URL}{series_path}/?{urlencode(params)}"


def _polite_sleep_if_needed() -> None:
    global _LAST_REQUEST_TS
    min_interval = _to_float("EIA_MIN_REQUEST_INTERVAL_SECONDS", DEFAULT_MIN_REQUEST_INTERVAL_SECONDS)
    now = time.monotonic()
    elapsed = now - _LAST_REQUEST_TS
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _LAST_REQUEST_TS = time.monotonic()


def _load_cache(cache_file: Path, ttl_seconds: int) -> dict[str, Any] | None:
    if not cache_file.exists():
        return None
    age = time.time() - cache_file.stat().st_mtime
    if age > ttl_seconds:
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _save_cache(cache_file: Path, payload: dict[str, Any]) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fetch_series(
    series_id: str,
    *,
    start: str | None = None,
    end: str | None = None,
    timeout: int = 20,
    length: int = 12,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Fetch JSON data for an EIA series path and return parsed payload."""
    ttl_seconds = _to_int("EIA_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS)
    cache_file = DEFAULT_CACHE_DIR / _cache_key(series_id, start, end, length)

    if not force_refresh:
        cached = _load_cache(cache_file, ttl_seconds)
        if cached:
            return cached

    url = build_series_url(series_id, start=start, end=end, length=length)
    req = Request(url, headers={"User-Agent": "DataByArea/1.1 (+https://databyarea.com)"})
    retries = _to_int("EIA_MAX_RETRIES", DEFAULT_MAX_RETRIES)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            _polite_sleep_if_needed()
            with urlopen(req, timeout=timeout) as response:  # nosec - URL is fixed EIA endpoint
                body = response.read().decode("utf-8")
            payload = json.loads(body)
            if "error" in payload:
                raise EIAClientError(str(payload["error"]))
            _save_cache(cache_file, payload)
            return payload
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, EIAClientError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(min(4.0, 0.5 * (2**attempt)))

    raise EIAClientError(f"Unable to fetch series '{series_id}': {last_error}")


def save_snapshot(
    series_id: str,
    out_path: str | Path,
    *,
    start: str | None = None,
    end: str | None = None,
    length: int = 12,
    force_refresh: bool = False,
) -> Path:
    """Fetch a series and write it to a local JSON snapshot file."""
    payload = fetch_series(
        series_id,
        start=start,
        end=end,
        length=length,
        force_refresh=force_refresh,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def init_storage(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    """Initialize sqlite storage for API points."""
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_series_points (
                series_id TEXT NOT NULL,
                period TEXT NOT NULL,
                value REAL,
                units TEXT,
                fetched_at TEXT NOT NULL,
                source TEXT NOT NULL,
                PRIMARY KEY (series_id, period)
            )
            """
        )
    return db


def upsert_series_points(
    payload: dict[str, Any],
    *,
    series_id: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    """Upsert rows from EIA payload into sqlite storage."""
    response = payload.get("response", {})
    data_rows = response.get("data") or []
    if not isinstance(data_rows, list):
        return 0

    units = response.get("units")
    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    db = init_storage(db_path)

    stored = 0
    with sqlite3.connect(db) as conn:
        for row in data_rows:
            if not isinstance(row, dict):
                continue
            period = str(row.get("period", "")).strip()
            value = row.get("value")
            if not period:
                continue
            try:
                numeric_value = float(value) if value is not None else None
            except (TypeError, ValueError):
                numeric_value = None
            conn.execute(
                """
                INSERT INTO api_series_points (series_id, period, value, units, fetched_at, source)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(series_id, period)
                DO UPDATE SET
                  value = excluded.value,
                  units = excluded.units,
                  fetched_at = excluded.fetched_at,
                  source = excluded.source
                """,
                (series_id, period, numeric_value, units, fetched_at, "eia:v2"),
            )
            stored += 1

    return stored


def get_latest_points(db_path: str | Path = DEFAULT_DB_PATH, *, limit: int = 200) -> list[tuple[str, str, float | None, str | None]]:
    """Get most recent points from local sqlite storage."""
    db = Path(db_path)
    if not db.exists():
        return []
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            """
            SELECT series_id, period, value, units
            FROM api_series_points
            ORDER BY period DESC, series_id ASC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
    return [(str(r[0]), str(r[1]), r[2], r[3]) for r in rows]
