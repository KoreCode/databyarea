#!/usr/bin/env python3
"""Tiny EIA API client used by DataByArea automation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

EIA_API_URL = "https://api.eia.gov/v2/"
DEFAULT_EIA_API_KEY = "2OKDrEV0VEb6XGdTbFfRVXzEzIdnBMbhJyTGjtog"


class EIAClientError(RuntimeError):
    """Raised for recoverable EIA API errors."""


def resolve_api_key() -> str:
    """Resolve EIA API key from env, falling back to configured project key."""
    return os.getenv("EIA_API_KEY", DEFAULT_EIA_API_KEY).strip()


def build_series_url(series_id: str, *, start: str | None = None, end: str | None = None) -> str:
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
        "length": 12,
    }
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    series_path = series_id.strip("/")
    return f"{EIA_API_URL}{series_path}/?{urlencode(params)}"


def fetch_series(series_id: str, *, start: str | None = None, end: str | None = None, timeout: int = 20) -> dict[str, Any]:
    """Fetch JSON data for an EIA series path and return parsed payload."""
    url = build_series_url(series_id, start=start, end=end)
    req = Request(url, headers={"User-Agent": "DataByArea/1.0"})
    with urlopen(req, timeout=timeout) as response:  # nosec - URL is fixed EIA endpoint
        body = response.read().decode("utf-8")
    payload = json.loads(body)
    if "error" in payload:
        raise EIAClientError(str(payload["error"]))
    return payload


def save_snapshot(series_id: str, out_path: str | Path, *, start: str | None = None, end: str | None = None) -> Path:
    """Fetch a series and write it to a local JSON snapshot file."""
    payload = fetch_series(series_id, start=start, end=end)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out
