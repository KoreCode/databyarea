#!/usr/bin/env python3
"""Run multi-agent quality checks and optional site generation for DataByArea."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "_deploy" / "agent_quality_report.json"


def run_cmd(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "cmd": cmd,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def agent_code_guardian() -> dict[str, Any]:
    scripts = [
        "admin_backend.py",
        "one_button_daily.py",
        "publish_popular_cities_daily.py",
        "scripts/build_site.py",
        "scripts/site_quality_agents.py",
        "scripts/eia_client.py",
    ]
    cmd = [sys.executable, "-m", "py_compile", *scripts]
    return {"agent": "Code Guardian", "task": "Python syntax validation", "result": run_cmd(cmd)}


def agent_site_builder(enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {
            "agent": "Site Builder",
            "task": "Generate site pages",
            "result": {"ok": True, "skipped": True, "note": "Generation disabled. Use --generate."},
        }
    return {
        "agent": "Site Builder",
        "task": "Generate site pages",
        "result": run_cmd([sys.executable, "scripts/build_site.py"]),
    }


def agent_seo_auditor() -> dict[str, Any]:
    required = [REPO_ROOT / "index.html", REPO_ROOT / "sitemap.xml", REPO_ROOT / "robots.txt"]
    missing = [str(p.relative_to(REPO_ROOT)) for p in required if not p.exists()]
    return {
        "agent": "SEO Auditor",
        "task": "Check critical crawl/index files",
        "result": {
            "ok": not missing,
            "missing": missing,
            "checked": [str(p.relative_to(REPO_ROOT)) for p in required],
        },
    }


def agent_content_guardian() -> dict[str, Any]:
    categories = ["insurance-costs", "utility-costs", "property-taxes", "cost-of-living"]
    counts = {}
    for category in categories:
        root = REPO_ROOT / category
        counts[category] = len(list(root.glob("*/index.html"))) if root.exists() else 0
    return {
        "agent": "Visitor Happiness Analyst",
        "task": "Check breadth of state landing pages",
        "result": {"ok": all(v >= 50 for v in counts.values()), "state_pages_per_category": counts},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multi-agent quality checks and optional generation.")
    parser.add_argument("--generate", action="store_true", help="Also run the site generator agent.")
    args = parser.parse_args()

    checks = [
        agent_code_guardian(),
        agent_site_builder(enabled=args.generate),
        agent_seo_auditor(),
        agent_content_guardian(),
    ]
    overall_ok = all((item.get("result") or {}).get("ok", False) for item in checks)

    report = {
        "ran_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_ok": overall_ok,
        "checks": checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote quality report: {REPORT_PATH}")
    print(json.dumps(report, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
