#!/usr/bin/env python3
"""Validate DataByArea template data records.

This is intentionally dependency-free so it can run in CI, Cloudflare build
hooks, or a local Windows shell without installing a JSON schema package.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CITY_ROOT = ROOT / "data" / "places"
STATE_INSIGHT_ROOT = ROOT / "data" / "state-insights"
METRIC_DEFINITIONS_PATH = ROOT / "data" / "metric_definitions.json"

REQUIRED_CITY_TOP_LEVEL = {
    "schema_version",
    "updated_at",
    "location",
    "page",
    "metrics",
    "sources",
}
REQUIRED_LOCATION_KEYS = {"type", "name", "slug", "state_name", "state_slug", "state_abbr", "country"}
REQUIRED_PAGE_KEYS = {"canonical_path", "api_path", "title", "description", "robots"}
REQUIRED_METRIC_KEYS = {
    "value",
    "unit",
    "display",
    "label",
    "source_id",
    "source_year",
    "updated_at",
    "confidence",
    "status",
}
VALID_CONFIDENCE = {"high", "medium", "low", "estimated", "placeholder"}
VALID_STATUS = {"actual", "estimate", "fallback", "unavailable"}


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path}: invalid JSON: {exc}") from exc


def require_keys(path: Path, scope: str, obj: dict[str, Any], keys: set[str]) -> None:
    missing = sorted(keys - set(obj))
    if missing:
        raise ValidationError(f"{path}: {scope} missing required keys: {', '.join(missing)}")


def validate_metric(path: Path, metric_key: str, metric: dict[str, Any], sources: dict[str, Any]) -> None:
    require_keys(path, f"metrics.{metric_key}", metric, REQUIRED_METRIC_KEYS)
    if metric["source_id"] not in sources:
        raise ValidationError(f"{path}: metrics.{metric_key}.source_id references missing source {metric['source_id']!r}")
    if metric["confidence"] not in VALID_CONFIDENCE:
        raise ValidationError(f"{path}: metrics.{metric_key}.confidence has invalid value {metric['confidence']!r}")
    if metric["status"] not in VALID_STATUS:
        raise ValidationError(f"{path}: metrics.{metric_key}.status has invalid value {metric['status']!r}")
    aliases = metric.get("aliases", [])
    if aliases is not None and not isinstance(aliases, list):
        raise ValidationError(f"{path}: metrics.{metric_key}.aliases must be a list when present")


def validate_city_record(path: Path, metric_definitions: dict[str, Any]) -> None:
    data = load_json(path)
    require_keys(path, "record", data, REQUIRED_CITY_TOP_LEVEL)
    if data["schema_version"] != "dba.location.v1":
        raise ValidationError(f"{path}: unsupported schema_version {data['schema_version']!r}")

    require_keys(path, "location", data["location"], REQUIRED_LOCATION_KEYS)
    require_keys(path, "page", data["page"], REQUIRED_PAGE_KEYS)

    metrics = data["metrics"]
    sources = data["sources"]
    if not isinstance(metrics, dict) or not metrics:
        raise ValidationError(f"{path}: metrics must be a non-empty object")
    if not isinstance(sources, dict) or not sources:
        raise ValidationError(f"{path}: sources must be a non-empty object")

    known_metrics = set(metric_definitions.get("metrics", {}))
    for metric_key, metric in metrics.items():
        validate_metric(path, metric_key, metric, sources)
        if metric_key not in known_metrics:
            print(f"WARN {path}: metric {metric_key!r} is not in data/metric_definitions.json")

    for section, metric_keys in data.get("sections", {}).items():
        if not isinstance(metric_keys, list):
            raise ValidationError(f"{path}: sections.{section} must be a list")
        missing = [key for key in metric_keys if key not in metrics]
        if missing:
            raise ValidationError(f"{path}: sections.{section} references missing metrics: {', '.join(missing)}")

    for chart_key, chart in data.get("charts", {}).items():
        if chart.get("source_id") not in sources:
            raise ValidationError(f"{path}: charts.{chart_key}.source_id references missing source {chart.get('source_id')!r}")
        if not isinstance(chart.get("points", []), list):
            raise ValidationError(f"{path}: charts.{chart_key}.points must be a list")


def validate_state_insight(path: Path) -> None:
    data = load_json(path)
    require_keys(path, "record", data, {"schema_version", "updated_at", "state", "page", "metrics", "sources"})
    if data["schema_version"] != "dba.state_insight.v1":
        raise ValidationError(f"{path}: unsupported schema_version {data['schema_version']!r}")
    require_keys(path, "state", data["state"], {"name", "slug", "abbr", "country"})
    require_keys(path, "page", data["page"], {"state_hub_path", "insight_paths"})
    for metric_key, metric in data["metrics"].items():
        validate_metric(path, metric_key, metric, data["sources"])


def iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", action="append", default=[], help="Specific city data JSON path to validate")
    parser.add_argument("--state-insight", action="append", default=[], help="Specific state insight JSON path to validate")
    args = parser.parse_args()

    metric_definitions = load_json(METRIC_DEFINITIONS_PATH)
    city_paths = [ROOT / item for item in args.city] if args.city else iter_json_files(CITY_ROOT)
    state_paths = [ROOT / item for item in args.state_insight] if args.state_insight else iter_json_files(STATE_INSIGHT_ROOT)

    errors: list[str] = []
    for path in city_paths:
        try:
            validate_city_record(path, metric_definitions)
        except ValidationError as exc:
            errors.append(str(exc))

    for path in state_paths:
        try:
            validate_state_insight(path)
        except ValidationError as exc:
            errors.append(str(exc))

    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1

    print(f"Validated {len(city_paths)} city record(s) and {len(state_paths)} state insight record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
