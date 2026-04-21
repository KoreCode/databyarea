#!/usr/bin/env python3
"""Run multi-agent quality checks and optional site generation for DataByArea."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "_deploy" / "agent_quality_report.json"
DAILY_SUMMARY_JSON = REPO_ROOT / "_deploy" / "last_daily_run_summary.json"
DAILY_SUMMARY_MD = REPO_ROOT / "_deploy" / "last_daily_run_summary.md"
SITE_URL = "https://databyarea.com"


TITLE_RE = re.compile(r"<title[^>]*>.*?</title>", re.IGNORECASE | re.DOTALL)
META_DESC_RE = re.compile(
    r"<meta[^>]+name=[\"']description[\"'][^>]*content=[\"'][^\"']+[\"'][^>]*>",
    re.IGNORECASE,
)
CANONICAL_RE = re.compile(
    r"<link[^>]+rel=[\"']canonical[\"'][^>]*href=[\"']([^\"']+)[\"'][^>]*>",
    re.IGNORECASE,
)
JSONLD_RE = re.compile(
    r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>.*?</script>",
    re.IGNORECASE | re.DOTALL,
)
ANCHOR_HREF_RE = re.compile(r"<a\s+[^>]*href=[\"']([^\"']+)[\"']", re.IGNORECASE)


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


def load_daily_summary() -> dict[str, Any]:
    if not DAILY_SUMMARY_JSON.exists():
        return {}
    try:
        return json.loads(DAILY_SUMMARY_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def should_require_jsonld(path: str) -> bool:
    if path == "/":
        return True
    parts = [p for p in path.split("/") if p]
    if not parts:
        return False
    page_types = {"insurance-costs", "utility-costs", "property-taxes", "cost-of-living"}
    return parts[0] in page_types


def normalize_site_path(href: str, current_path: str) -> str | None:
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None

    parsed = urlparse(href)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return None

    if parsed.netloc and parsed.netloc not in {"databyarea.com", "www.databyarea.com"}:
        return None

    if parsed.path.startswith("/"):
        path = parsed.path
    else:
        base = current_path if current_path.endswith("/") else f"{current_path}/"
        path = urlparse(urljoin(base, parsed.path)).path

    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and not path.endswith("/"):
        path += "/"
    return path


def site_path_to_file(path: str) -> Path:
    if path == "/":
        return REPO_ROOT / "index.html"
    rel = path.strip("/")
    return REPO_ROOT / rel / "index.html"


def evaluate_newly_published_paths() -> dict[str, Any]:
    summary = load_daily_summary()
    new_paths: list[str] = summary.get("new_url_paths") or []
    issues = {
        "missing_title_or_meta_description": [],
        "canonical_mismatch": [],
        "missing_jsonld": [],
        "broken_internal_links": [],
        "missing_files": [],
    }

    for page_path in new_paths:
        file_path = site_path_to_file(page_path)
        if not file_path.exists():
            issues["missing_files"].append({"path": page_path, "expected_file": str(file_path.relative_to(REPO_ROOT))})
            continue

        html = file_path.read_text(encoding="utf-8", errors="ignore")

        has_title = bool(TITLE_RE.search(html))
        has_meta_desc = bool(META_DESC_RE.search(html))
        if not has_title or not has_meta_desc:
            issues["missing_title_or_meta_description"].append(
                {"path": page_path, "missing_title": not has_title, "missing_meta_description": not has_meta_desc}
            )

        expected_canonical = f"{SITE_URL.rstrip('/')}{page_path}"
        canonical_match = CANONICAL_RE.search(html)
        actual_canonical = canonical_match.group(1).strip() if canonical_match else ""
        if actual_canonical.rstrip("/") != expected_canonical.rstrip("/"):
            issues["canonical_mismatch"].append(
                {
                    "path": page_path,
                    "expected": expected_canonical,
                    "actual": actual_canonical or None,
                }
            )

        if should_require_jsonld(page_path) and not JSONLD_RE.search(html):
            issues["missing_jsonld"].append({"path": page_path})

        broken_links: list[str] = []
        for href in ANCHOR_HREF_RE.findall(html):
            target_path = normalize_site_path(href.strip(), page_path)
            if target_path is None:
                continue
            target_file = site_path_to_file(target_path)
            if not target_file.exists():
                broken_links.append(href)

        if broken_links:
            issues["broken_internal_links"].append(
                {
                    "path": page_path,
                    "broken_links": sorted(set(broken_links))[:30],
                    "broken_links_count": len(set(broken_links)),
                }
            )

    has_issues = any(bool(v) for v in issues.values())
    return {
        "agent": "Publish Gate Auditor",
        "task": "Validate newly published pages for metadata, canonical, schema, and internal links",
        "result": {
            "ok": not has_issues,
            "checked_new_paths": len(new_paths),
            "issues": issues,
        },
    }


def write_daily_gate_summary(report: dict[str, Any]) -> None:
    prior = load_daily_summary()
    checks = report.get("checks", [])
    failed_checks = [c for c in checks if not (c.get("result") or {}).get("ok", False)]

    prior["quality_gate"] = {
        "ran_at_utc": report.get("ran_at_utc"),
        "overall_ok": report.get("overall_ok", False),
        "report_path": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "checks_count": len(checks),
        "failed_checks_count": len(failed_checks),
        "failed_checks": [
            {
                "agent": c.get("agent"),
                "task": c.get("task"),
            }
            for c in failed_checks
        ],
    }
    DAILY_SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    DAILY_SUMMARY_JSON.write_text(json.dumps(prior, indent=2), encoding="utf-8")

    md_lines = [
        "# Daily Runner Summary",
        "",
        f"- Date (UTC): `{prior.get('date_utc', 'n/a')}`",
        f"- Generator: `{prior.get('generator', 'n/a')}`",
        f"- City pages created: `{prior.get('created_city_urls_count', 0)}`",
        f"- New manifest slugs: `{prior.get('new_manifest_slugs_count', 0)}`",
        f"- New index pages: `{prior.get('new_url_paths_count', 0)}`",
        f"- Sitemap URLs total: `{prior.get('sitemap_urls_total', 'n/a')}`",
        f"- Deploy zip: `{prior.get('deploy_zip', 'n/a')}`",
        "",
        "## Return Codes",
        f"- city publisher: `{prior.get('city_rc')}`",
        f"- generator: `{prior.get('make_rc')}`",
        f"- relink: `{prior.get('relink_rc')}`",
        f"- clean: `{prior.get('clean_rc')}`",
        "",
        "## Publish Quality Gate",
        f"- Ran at (UTC): `{report.get('ran_at_utc')}`",
        f"- Overall gate status: `{'PASS' if report.get('overall_ok') else 'FAIL'}`",
        f"- Checks run: `{len(checks)}`",
        f"- Failed checks: `{len(failed_checks)}`",
    ]
    if failed_checks:
        md_lines.extend(["", "### Failed Checks"])
        for failed in failed_checks:
            md_lines.append(f"- `{failed.get('agent')}` — {failed.get('task')}")

    DAILY_SUMMARY_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multi-agent quality checks and optional generation.")
    parser.add_argument("--generate", action="store_true", help="Also run the site generator agent.")
    args = parser.parse_args()

    checks = [
        agent_code_guardian(),
        agent_site_builder(enabled=args.generate),
        agent_seo_auditor(),
        agent_content_guardian(),
        evaluate_newly_published_paths(),
    ]
    overall_ok = all((item.get("result") or {}).get("ok", False) for item in checks)

    report = {
        "ran_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_ok": overall_ok,
        "checks": checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_daily_gate_summary(report)

    print(f"Wrote quality report: {REPORT_PATH}")
    print(f"Updated daily summary files: {DAILY_SUMMARY_JSON} and {DAILY_SUMMARY_MD}")
    print(json.dumps(report, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
