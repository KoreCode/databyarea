#!/usr/bin/env python3
"""Production readiness checks for the static DataByArea repo.

This script is intentionally dependency-free so GitHub Actions and Cloudflare
build environments can run it without a package install step.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "_deploy" / "reports" / "production_check.json"

SKIP_DIRS = {".git", "__pycache__", "node_modules", "_deploy", "_trash", "service-guides"}
TEXT_SUFFIXES = {
    ".html",
    ".css",
    ".js",
    ".mjs",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".ps1",
    ".yml",
    ".yaml",
    ".txt",
    ".csv",
    ".xml",
}
CRITICAL_PAGES = [
    "/",
    "/search/",
    "/minnesota/",
    "/minnesota/kiester-template/",
    "/cost-of-living/",
    "/utility-costs/",
    "/property-taxes/",
    "/insurance-costs/",
    "/service-guides/",
    "/service-guides/electrician/",
    "/service-guides/electrician/minnesota/",
    "/service-guides/electrician/minnesota/lake-city/",
    "/service-guides/electrician/minnesota/lake-city/new-outlets/",
    "/cost-of-living/minnesota/",
    "/utility-costs/minnesota/",
    "/property-taxes/minnesota/",
    "/insurance-costs/minnesota/",
]
PYTHON_ENTRYPOINTS = [
    "admin_backend.py",
    "one_button_daily.py",
    "publish_popular_cities_daily.py",
    "scripts/build_search_index.py",
    "scripts/build_site.py",
    "scripts/check_conflict_markers.py",
    "scripts/content_distribution_workflow.py",
    "scripts/eia_client.py",
    "scripts/eia_pipeline.py",
    "scripts/generate_service_guides.py",
    "scripts/production_check.py",
    "scripts/run_production_gates.py",
    "scripts/service_guide_data.py",
    "scripts/site_quality_agents.py",
    "scripts/validate_data_layer.py",
    "scripts/weekly_kpi_report.py",
]
SECRET_PATTERNS = [
    re.compile(r"DEFAULT_[A-Z0-9_]*API_KEY\s*=\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]", re.I),
    re.compile(r"bearer\s+[A-Za-z0-9_\-\.]{24,}", re.I),
]
ANCHOR_HREF_RE = re.compile(r"<a\s+[^>]*href=[\"']([^\"']+)[\"']", re.I)
TITLE_RE = re.compile(r"<title[^>]*>.+?</title>", re.I | re.S)
META_DESC_RE = re.compile(r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"'][^\"']+[\"']", re.I)


def is_skipped(path: Path) -> bool:
    rel_parts = path.relative_to(REPO_ROOT).parts
    return any(part in SKIP_DIRS for part in rel_parts)


def text_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or is_skipped(path):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"robots.txt", "sitemap.xml"}:
            files.append(path)
    return files


def run_cmd(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-3000:],
        "stderr_tail": (proc.stderr or "")[-3000:],
    }


def site_path_to_file(path: str) -> Path:
    if path == "/":
        return REPO_ROOT / "index.html"
    return REPO_ROOT / path.strip("/") / "index.html"


def normalize_internal_href(href: str, current_path: str) -> str | None:
    href = href.strip()
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

    if path == "":
        path = "/"
    if path != "/" and not path.endswith("/"):
        path += "/"
    return path


def check_python_compile() -> dict[str, Any]:
    existing = [p for p in PYTHON_ENTRYPOINTS if (REPO_ROOT / p).exists()]
    result = run_cmd([sys.executable, "-m", "py_compile", *existing])
    return {"ok": result["ok"], "checked": existing, "result": result}


def check_data_layer() -> dict[str, Any]:
    validator = REPO_ROOT / "scripts" / "validate_data_layer.py"
    if not validator.exists():
        return {"ok": False, "error": "scripts/validate_data_layer.py is missing"}
    result = run_cmd([sys.executable, str(validator.relative_to(REPO_ROOT))])
    return {"ok": result["ok"], "result": result}


def check_json_files() -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    checked = 0
    for path in text_files():
        if path.suffix.lower() != ".json":
            continue
        checked += 1
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            failures.append({"path": path.relative_to(REPO_ROOT).as_posix(), "error": str(exc)})
    return {"ok": not failures, "checked": checked, "failures": failures[:50]}


def check_workflows() -> dict[str, Any]:
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    failures: list[str] = []
    checked: list[str] = []
    if not workflow_dir.exists():
        return {"ok": False, "failures": [".github/workflows is missing"]}

    for path in sorted(workflow_dir.glob("*.y*ml")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        checked.append(rel)
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "uses: actions/checkout@v4" not in text:
            failures.append(f"{rel}: missing actions/checkout@v4")
        if "uses: actions/setup-python@v5" in text and "python-version:" not in text:
            failures.append(f"{rel}: setup-python is missing python-version")
        if "contents: write" in text and "concurrency:" not in text:
            failures.append(f"{rel}: write workflow is missing concurrency")
        if "git push" in text and "git diff --cached --quiet" not in text:
            failures.append(f"{rel}: pushes without cached diff guard")
        if "run_daily.sh" in text and "bash ./run_daily.sh" not in text:
            failures.append(f"{rel}: should call run_daily.sh through bash")
    return {"ok": not failures, "checked": checked, "failures": failures}


def check_secrets() -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for path in text_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel == "README.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(text.splitlines(), start=1):
            if "secrets." in line or "${{" in line:
                continue
            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append({"path": rel, "line": str(idx), "match": pattern.pattern})
                    break
    return {"ok": not findings, "findings": findings[:50]}


def check_critical_pages() -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    for page in CRITICAL_PAGES:
        file_path = site_path_to_file(page)
        if not file_path.exists():
            failures.append({"path": page, "error": "missing index.html"})
            continue
        html = file_path.read_text(encoding="utf-8", errors="ignore")
        missing: list[str] = []
        if not TITLE_RE.search(html):
            missing.append("title")
        if not META_DESC_RE.search(html):
            missing.append("meta description")
        if "/assets/search-autocomplete.js" not in html and page in {"/", "/search/"} | {p for p in CRITICAL_PAGES if p.startswith(("/cost-of-living", "/utility-costs", "/property-taxes", "/insurance-costs"))}:
            missing.append("search autocomplete script")

        broken_links: list[str] = []
        for href in ANCHOR_HREF_RE.findall(html):
            target = normalize_internal_href(href, page)
            if target is None:
                continue
            if not site_path_to_file(target).exists():
                broken_links.append(href)

        if missing or broken_links:
            failures.append(
                {
                    "path": page,
                    "missing": missing,
                    "broken_internal_links": sorted(set(broken_links))[:25],
                    "broken_internal_links_count": len(set(broken_links)),
                }
            )
    return {"ok": not failures, "checked": CRITICAL_PAGES, "failures": failures}


def check_search_index() -> dict[str, Any]:
    path = REPO_ROOT / "assets" / "search-index.json"
    if not path.exists():
        return {"ok": False, "error": "assets/search-index.json is missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": str(exc)}

    states = payload.get("states") if isinstance(payload, dict) else None
    items = payload.get("items") if isinstance(payload, dict) else None
    failures: list[str] = []
    if not isinstance(states, list) or len(states) < 50:
        failures.append("expected at least 50 states/district entries")
    if not isinstance(items, list) or not items:
        failures.append("expected non-empty search items")
    else:
        city_profiles = [item for item in items if item.get("category") == "city-dashboard"]
        if not city_profiles:
            failures.append("expected at least one city-dashboard search item")
        for item in items[:100]:
            url = str(item.get("url", ""))
            if url and url.startswith("/") and not site_path_to_file(url).exists():
                failures.append(f"search item points to missing page: {url}")
                break
    return {
        "ok": not failures,
        "states_count": len(states or []),
        "items_count": len(items or []),
        "failures": failures,
    }


def check_common_text_damage() -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    bad_tokens = ("\u00c2", "\u00e2\u20ac\u201d", "\u00e2\u20ac\u201c", "\u00e2\u20ac\u2122", "\u00e2\u2020")
    for path in text_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(text.splitlines(), start=1):
            if any(token in line for token in bad_tokens):
                findings.append({"path": rel, "line": str(idx), "sample": line[:160]})
                break
    return {"ok": not findings, "findings": findings[:100]}


def main() -> int:
    required_checks = {
        "python_compile": check_python_compile(),
        "data_layer": check_data_layer(),
        "json_files": check_json_files(),
        "workflows": check_workflows(),
        "secret_scan": check_secrets(),
        "critical_pages": check_critical_pages(),
        "search_index": check_search_index(),
    }
    advisory_checks = {
        "text_encoding_damage": check_common_text_damage(),
    }
    overall_ok = all(check.get("ok") for check in required_checks.values())
    report = {
        "ran_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_ok": overall_ok,
        "required_checks": required_checks,
        "advisory_checks": advisory_checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
