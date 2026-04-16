#!/usr/bin/env python3
"""Fast API pipeline: pull EIA data, store in sqlite, and render dashboard HTML."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

from eia_client import (
    DEFAULT_DB_PATH,
    fetch_series,
    get_latest_points,
    init_storage,
    save_snapshot,
    upsert_series_points,
)

DEFAULT_SERIES = [
    "electricity/retail-sales/data",
    "electricity/retail-sales/state-end-use/data",
]
DEFAULT_DASHBOARD_PATH = Path("site/api-dashboard/index.html")


def render_dashboard(out_path: str | Path, *, db_path: str | Path = DEFAULT_DB_PATH, limit: int = 100) -> Path:
    rows = get_latest_points(db_path, limit=limit)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if rows:
        body_rows = "\n".join(
            f"<tr><td>{escape(series)}</td><td>{escape(period)}</td><td>{value if value is not None else 'n/a'}</td><td>{escape(units or 'n/a')}</td></tr>"
            for series, period, value, units in rows
        )
    else:
        body_rows = "<tr><td colspan='4'>No data yet. Run the pipeline pull step.</td></tr>"

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>API Data Dashboard | DataByArea</title>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; margin: 2rem; color: #0f172a; }}
    h1 {{ margin-bottom: 0.25rem; }}
    p {{ color: #334155; }}
    .card {{ border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 0.7rem; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 0.95rem; }}
    th {{ background: #f8fafc; }}
    tr:hover td {{ background: #f8fafc; }}
  </style>
</head>
<body>
  <h1>DataByArea API Dashboard</h1>
  <p>Recent locally stored values from EIA v2 API with cached + rate-limited retrieval.</p>
  <div class=\"card\">
    <table>
      <thead><tr><th>Series</th><th>Period</th><th>Value</th><th>Units</th></tr></thead>
      <tbody>{body_rows}</tbody>
    </table>
  </div>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    return out


def run_pull(series_ids: list[str], *, snapshots_dir: Path, db_path: Path, length: int, force_refresh: bool) -> None:
    init_storage(db_path)
    for series_id in series_ids:
        payload = fetch_series(series_id, length=length, force_refresh=force_refresh)
        stored = upsert_series_points(payload, series_id=series_id, db_path=db_path)
        snapshot_name = series_id.strip("/").replace("/", "__") + ".json"
        save_snapshot(
            series_id,
            snapshots_dir / snapshot_name,
            length=length,
            force_refresh=False,
        )
        print(f"[ok] {series_id}: stored={stored} snapshot={snapshots_dir / snapshot_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pull, store, and render EIA data quickly and safely.")
    parser.add_argument("--series", nargs="+", default=DEFAULT_SERIES, help="EIA v2 series path(s)")
    parser.add_argument("--length", type=int, default=24, help="Rows to request per series")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="sqlite storage path")
    parser.add_argument("--snapshots-dir", default="data/api_snapshots", help="where JSON snapshots are written")
    parser.add_argument("--dashboard", default=str(DEFAULT_DASHBOARD_PATH), help="dashboard HTML output path")
    parser.add_argument("--skip-pull", action="store_true", help="skip API pull and only render from local db")
    parser.add_argument("--force-refresh", action="store_true", help="ignore cache and fetch fresh API responses")
    parser.add_argument("--limit", type=int, default=120, help="rows to render in dashboard")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    snapshots_dir = Path(args.snapshots_dir)

    if not args.skip_pull:
        run_pull(
            args.series,
            snapshots_dir=snapshots_dir,
            db_path=db_path,
            length=args.length,
            force_refresh=args.force_refresh,
        )
    out = render_dashboard(args.dashboard, db_path=db_path, limit=args.limit)
    print(f"[ok] dashboard={out}")


if __name__ == "__main__":
    main()
