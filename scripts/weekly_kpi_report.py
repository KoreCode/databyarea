#!/usr/bin/env python3
"""Generate and optionally deliver weekly KPI report."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "weekly_kpi_inputs.json"
REPORT_DIR = REPO_ROOT / "_deploy" / "reports"

REQUIRED_KEYS = ("traffic", "signups", "conversion_rate", "mrr", "churn_rate", "top_channels")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100.0


def format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def build_markdown(report: dict[str, Any]) -> str:
    current = report["current_week"]
    wow = report["week_over_week"]
    lines = [
        "# Weekly KPI Report",
        "",
        f"- Generated at (UTC): `{report['generated_at_utc']}`",
        f"- Coverage: `{report['period_start']} → {report['period_end']}`",
        "",
        "## Core KPIs",
        f"- Traffic: **{current['traffic']:,}** ({format_pct(wow['traffic'])} WoW)",
        f"- Signups: **{current['signups']:,}** ({format_pct(wow['signups'])} WoW)",
        f"- Conversion: **{current['conversion_rate']:.2%}** ({format_pct(wow['conversion_rate'])} WoW)",
        f"- MRR: **{format_currency(current['mrr'])}** ({format_pct(wow['mrr'])} WoW)",
        f"- Churn: **{current['churn_rate']:.2%}** ({format_pct(wow['churn_rate'])} WoW)",
        "",
        "## Top Channels",
    ]
    for idx, row in enumerate(current["top_channels"], start=1):
        lines.append(
            f"- {idx}. {row['channel']} — traffic `{row['traffic']:,}`, signups `{row['signups']:,}`, conversion `{row['conversion_rate']:.2%}`"
        )
    return "\n".join(lines) + "\n"


def send_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            status = getattr(resp, "status", 200)
            return 200 <= status < 300, f"HTTP {status}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate weekly KPI report.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to weekly KPI input JSON")
    parser.add_argument("--webhook-url", default=os.getenv("DBA_KPI_WEBHOOK_URL", ""), help="Optional webhook URL")
    parser.add_argument("--dry-run", action="store_true", help="Do not send webhook even if configured")
    args = parser.parse_args()

    payload = load_json(Path(args.input), {})
    if not isinstance(payload, dict):
        raise SystemExit("Invalid KPI JSON payload")

    current = payload.get("current_week", {})
    previous = payload.get("previous_week", {})

    missing = [key for key in REQUIRED_KEYS if key not in current]
    if missing:
        raise SystemExit(f"Current week payload missing required fields: {', '.join(missing)}")

    generated_at = datetime.now(timezone.utc).isoformat()
    period_start = str(payload.get("period_start", "unknown"))
    period_end = str(payload.get("period_end", "unknown"))

    wow = {
        "traffic": pct_change(float(current["traffic"]), float(previous.get("traffic", 0))),
        "signups": pct_change(float(current["signups"]), float(previous.get("signups", 0))),
        "conversion_rate": pct_change(float(current["conversion_rate"]), float(previous.get("conversion_rate", 0))),
        "mrr": pct_change(float(current["mrr"]), float(previous.get("mrr", 0))),
        "churn_rate": pct_change(float(current["churn_rate"]), float(previous.get("churn_rate", 0))),
    }

    report = {
        "generated_at_utc": generated_at,
        "period_start": period_start,
        "period_end": period_end,
        "current_week": current,
        "previous_week": previous,
        "week_over_week": wow,
        "delivery": {"attempted": False, "ok": None, "detail": "not requested"},
    }

    week_label = period_end if period_end != "unknown" else datetime.now(timezone.utc).date().isoformat()
    json_path = REPORT_DIR / f"weekly_kpi_{week_label}.json"
    md_path = REPORT_DIR / f"weekly_kpi_{week_label}.md"

    save_json(json_path, report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(build_markdown(report), encoding="utf-8")

    webhook_url = args.webhook_url.strip()
    if webhook_url and not args.dry_run:
        ok, detail = send_webhook(webhook_url, report)
        report["delivery"] = {"attempted": True, "ok": ok, "detail": detail}
        save_json(json_path, report)

    latest_pointer = REPORT_DIR / "latest_weekly_kpi_report.json"
    save_json(latest_pointer, report)

    print(f"Wrote report JSON: {json_path}")
    print(f"Wrote report Markdown: {md_path}")
    print(f"Delivery status: {report['delivery']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
