from collections import defaultdict
from pathlib import Path
import re
from .utils import norm

class ValidationError(Exception):
    pass


REQUIRED_SEO_PATTERNS = {
    "title": re.compile(r"<title>.+?</title>", re.IGNORECASE | re.DOTALL),
    "meta_description": re.compile(r'<meta[^>]+name=["\']description["\']', re.IGNORECASE),
    "canonical": re.compile(r'<link[^>]+rel=["\']canonical["\']', re.IGNORECASE),
    "og_title": re.compile(r'<meta[^>]+property=["\']og:title["\']', re.IGNORECASE),
    "twitter_card": re.compile(r'<meta[^>]+name=["\']twitter:card["\']', re.IGNORECASE),
    "jsonld": re.compile(r'<script[^>]+type=["\']application/ld\+json["\']', re.IGNORECASE),
}

def validate_high_intent(csv_rows: list[dict]):
    """
    Rules:
    - slug must be present and unique
    - topic must be present (topic column recommended) and unique
      (if topic missing, slug is used as topic)
    """
    seen_slugs = set()
    seen_topics = set()
    errors = []

    for i, row in enumerate(csv_rows, start=1):
        slug = norm(row.get("slug"))
        topic = norm(row.get("topic") or slug)

        if not slug:
            errors.append(f"Row {i}: missing slug")
            continue

        if slug in seen_slugs:
            errors.append(f"Row {i}: duplicate slug '{slug}'")
        seen_slugs.add(slug)

        if not topic:
            errors.append(f"Row {i}: missing topic (and slug could not be used)")
        elif topic in seen_topics:
            errors.append(f"Row {i}: duplicate topic '{topic}'")
        seen_topics.add(topic)

    if errors:
        raise ValidationError("\n".join(errors))


def validate_required_seo_fields(html: str, page_label: str = "") -> list[str]:
    missing = []
    for field, pattern in REQUIRED_SEO_PATTERNS.items():
        if not pattern.search(html):
            missing.append(field)
    if missing and page_label:
        return [f"{page_label}: missing {', '.join(missing)}"]
    return missing


def validate_generated_pages(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        if not path.exists():
            errors.append(f"{path.as_posix()}: file missing")
            continue
        html = path.read_text(encoding="utf-8", errors="ignore")
        errs = validate_required_seo_fields(html, page_label=path.as_posix())
        if errs:
            errors.extend(errs if isinstance(errs, list) else [str(errs)])
    return errors


def seo_coverage_report(paths: list[Path]) -> dict:
    counts = defaultdict(int)
    evaluated = 0
    for path in paths:
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8", errors="ignore")
        evaluated += 1
        for field, pattern in REQUIRED_SEO_PATTERNS.items():
            if pattern.search(html):
                counts[field] += 1
    return {
        "evaluated_pages": evaluated,
        "required_fields": sorted(REQUIRED_SEO_PATTERNS.keys()),
        "field_coverage": {
            field: {
                "present": counts.get(field, 0),
                "pct": round((counts.get(field, 0) / evaluated) * 100, 1) if evaluated else 0.0,
            }
            for field in sorted(REQUIRED_SEO_PATTERNS.keys())
        },
    }
