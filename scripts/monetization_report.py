#!/usr/bin/env python3
"""Generate monetization + SEO diagnostics for generated pages and persist trend history."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = REPO_ROOT / "_deploy"
LAST_SUMMARY_PATH = DEPLOY_DIR / "last_daily_run_summary.json"
LAST_REPORT_PATH = DEPLOY_DIR / "last_monetization_report.json"
TREND_HISTORY_PATH = DEPLOY_DIR / "monetization_report_history.json"
SUMMARY_HISTORY_PATH = DEPLOY_DIR / "daily_run_summary_history.json"
FLAGS_PATH = DEPLOY_DIR / "monetization_flags.json"

EXCLUDE_TOP_LEVEL = {"_deploy", ".git", "scripts", "assets", "admin", "data", "__pycache__"}
REQUIRED_DISCLOSURE_PATTERNS = [
    re.compile(r"affiliate", re.IGNORECASE),
    re.compile(r"sponsored", re.IGNORECASE),
    re.compile(r"advertis(?:ement|ing)", re.IGNORECASE),
    re.compile(r"commission", re.IGNORECASE),
    re.compile(r"disclosure", re.IGNORECASE),
]
MONETIZATION_PATTERNS = [
    re.compile(r"affiliate", re.IGNORECASE),
    re.compile(r"sponsored", re.IGNORECASE),
    re.compile(r"ad-slot|adsbygoogle|doubleclick|googlesyndication", re.IGNORECASE),
    re.compile(r"monetiz|commission", re.IGNORECASE),
]
SEO_FAILURE_RATE_THRESHOLD = 0.15
MAX_HISTORY = 120


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


def page_iter() -> list[tuple[str, Path, str]]:
    pages: list[tuple[str, Path, str]] = []
    for index_path in REPO_ROOT.glob("**/index.html"):
        rel = index_path.relative_to(REPO_ROOT)
        top = rel.parts[0] if rel.parts else ""
        if top in EXCLUDE_TOP_LEVEL:
            continue
        text = index_path.read_text(encoding="utf-8", errors="ignore")
        if len(rel.parts) == 1:
            url_path = "/"
            section = "root"
        else:
            url_path = "/" + "/".join(rel.parts[:-1]) + "/"
            section = rel.parts[0]
        pages.append((section, Path(url_path), text))
    return pages


def extract_template(url_path: Path) -> str:
    parts = [p for p in url_path.as_posix().strip("/").split("/") if p]
    if not parts:
        return "root"
    if len(parts) >= 3:
        return "city"
    if len(parts) == 2:
        return "state"
    return "index"


def find_seo_failures(html: str) -> list[str]:
    failures: list[str] = []
    if "<title>" not in html.lower():
        failures.append("missing_title")
    if 'name="description"' not in html.lower():
        failures.append("missing_meta_description")
    if "<h1" not in html.lower():
        failures.append("missing_h1")
    if "noindex" in html.lower():
        failures.append("contains_noindex")
    return failures


def detect_modules(html: str) -> set[str]:
    h = html.lower()
    modules = set()
    if "<h2>faq" in h or "<h3>faq" in h:
        modules.add("faq")
    if "related guides" in h or "keep exploring" in h:
        modules.add("internal_link_module")
    if any(p.search(html) for p in MONETIZATION_PATTERNS):
        modules.add("monetization_module")
    if any(p.search(html) for p in REQUIRED_DISCLOSURE_PATTERNS):
        modules.add("disclosure_module")
    return modules


def analyze_pages() -> dict[str, Any]:
    pages = page_iter()
    module_coverage: dict[str, Counter] = defaultdict(Counter)
    pages_missing_disclosure_labels: list[str] = []
    pages_exceeding_density_thresholds: list[dict[str, Any]] = []
    seo_failures: list[dict[str, Any]] = []
    monetized_count_by_template: Counter = Counter()

    for section, url_path, html in pages:
        modules = detect_modules(html)
        for module in modules:
            module_coverage[section][module] += 1
        module_coverage[section]["total_pages"] += 1

        seo_issues = find_seo_failures(html)
        if seo_issues:
            seo_failures.append({"url_path": url_path.as_posix(), "issues": seo_issues})

        marker_hits = sum(len(p.findall(html)) for p in MONETIZATION_PATTERNS)
        word_count = max(1, len(re.findall(r"\b\w+\b", html)))
        density_per_1k = (marker_hits / word_count) * 1000
        is_monetized = marker_hits > 0
        if is_monetized:
            monetized_count_by_template[extract_template(url_path)] += 1
            has_disclosure = any(p.search(html) for p in REQUIRED_DISCLOSURE_PATTERNS)
            if not has_disclosure:
                pages_missing_disclosure_labels.append(url_path.as_posix())
        if marker_hits >= 8 or density_per_1k > 12:
            pages_exceeding_density_thresholds.append(
                {
                    "url_path": url_path.as_posix(),
                    "monetization_markers": marker_hits,
                    "density_per_1000_words": round(density_per_1k, 2),
                }
            )

    return {
        "pages_published": len(pages),
        "pages_failing_seo_checks": len(seo_failures),
        "seo_failure_details": seo_failures,
        "module_coverage_by_section": {
            section: dict(counter) for section, counter in sorted(module_coverage.items())
        },
        "pages_missing_required_disclosure_labels": sorted(set(pages_missing_disclosure_labels)),
        "pages_exceeding_monetization_density_thresholds": pages_exceeding_density_thresholds,
        "monetized_pages_count_by_template": dict(monetized_count_by_template),
        "estimated_ctr": None,
        "estimated_rpm": None,
    }


def apply_rollback_if_needed(report: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    pages_published = report.get("pages_published", 0)
    pages_failing = report.get("pages_failing_seo_checks", 0)
    failure_rate = (pages_failing / pages_published) if pages_published else 0.0

    status: dict[str, Any] = {
        "threshold": SEO_FAILURE_RATE_THRESHOLD,
        "observed_failure_rate": round(failure_rate, 4),
        "triggered": False,
        "disabled_slugs": [],
    }

    summary = load_json(LAST_SUMMARY_PATH, {})
    newest_cohort = summary.get("new_manifest_slugs", []) or []

    if failure_rate <= SEO_FAILURE_RATE_THRESHOLD or not newest_cohort:
        return status

    flags = load_json(FLAGS_PATH, {"cohorts": []})
    disabled_slugs = []
    for slug in newest_cohort:
        disabled_slugs.append(slug)

    cohort_record = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "reason": "seo_failure_rate_exceeded_threshold",
        "threshold": SEO_FAILURE_RATE_THRESHOLD,
        "observed_failure_rate": round(failure_rate, 4),
        "disabled_slugs": disabled_slugs,
    }
    flags.setdefault("cohorts", []).append(cohort_record)
    flags["cohorts"] = flags["cohorts"][-MAX_HISTORY:]

    if not dry_run:
        save_json(FLAGS_PATH, flags)

    status["triggered"] = True
    status["disabled_slugs"] = disabled_slugs
    return status


def update_daily_summary(report: dict[str, Any], rollback_status: dict[str, Any]) -> None:
    summary = load_json(LAST_SUMMARY_PATH, {})
    if not summary:
        return

    summary["pages_published"] = report["pages_published"]
    summary["pages_failing_seo_checks"] = report["pages_failing_seo_checks"]
    summary["monetized_pages_count_by_template"] = report["monetized_pages_count_by_template"]
    summary["estimated_analytics_placeholders"] = {
        "estimated_ctr": report["estimated_ctr"],
        "estimated_rpm": report["estimated_rpm"],
        "status": "placeholder_for_future_analytics_ingestion",
    }
    summary["rollback_criteria"] = {
        "if_seo_failure_rate_gt": SEO_FAILURE_RATE_THRESHOLD,
        "action": "auto_disable_monetization_flags_for_newest_cohort",
    }
    summary["rollback_action"] = rollback_status
    save_json(LAST_SUMMARY_PATH, summary)

    history = load_json(SUMMARY_HISTORY_PATH, [])
    history.append(summary)
    history = history[-MAX_HISTORY:]
    save_json(SUMMARY_HISTORY_PATH, history)


def write_report(report: dict[str, Any], rollback_status: dict[str, Any]) -> None:
    payload = {
        "ran_at_utc": datetime.now(timezone.utc).isoformat(),
        **report,
        "seo_failure_rate": round(
            (report["pages_failing_seo_checks"] / report["pages_published"])
            if report["pages_published"]
            else 0.0,
            4,
        ),
        "rollback_action": rollback_status,
    }
    save_json(LAST_REPORT_PATH, payload)

    history = load_json(TREND_HISTORY_PATH, [])
    history.append(payload)
    history = history[-MAX_HISTORY:]
    save_json(TREND_HISTORY_PATH, history)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate monetization/SEO report and update daily summaries")
    parser.add_argument("--dry-run", action="store_true", help="Compute and print but do not persist rollback flag changes")
    args = parser.parse_args()

    report = analyze_pages()
    rollback_status = apply_rollback_if_needed(report, dry_run=args.dry_run)
    write_report(report, rollback_status)
    update_daily_summary(report, rollback_status)

    print(f"Wrote report: {LAST_REPORT_PATH}")
    print(f"Updated summary: {LAST_SUMMARY_PATH}")
    print(json.dumps({"report": report, "rollback_action": rollback_status}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
