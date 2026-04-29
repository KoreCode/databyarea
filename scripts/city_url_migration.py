"""Generate a concrete city URL migration map and optional redirect rules.

Maps legacy insight-specific city URLs to canonical city dashboard tab URLs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

INSIGHT_PREFIX_TO_TAB = {
    "utility-costs": "utilities",
    "insurance-costs": "insurance",
    "cost-of-living": "cost-of-living",
    "property-taxes": "property-taxes",
}


def _is_city_level_path(parts: Tuple[str, ...]) -> bool:
    return len(parts) >= 3 and parts[0] in INSIGHT_PREFIX_TO_TAB


def _legacy_to_canonical(path_parts: Tuple[str, ...]) -> Tuple[str, str]:
    service, state, city = path_parts[0], path_parts[1], path_parts[2]
    tab = INSIGHT_PREFIX_TO_TAB[service]
    legacy = f"/{service}/{state}/{city}/"
    canonical = f"/{state}/{city}/?tab={tab}"
    return legacy, canonical


def build_city_migration_map(root: Path) -> List[Dict[str, str]]:
    mappings: List[Dict[str, str]] = []
    seen = set()

    for insight_prefix in INSIGHT_PREFIX_TO_TAB:
        insight_dir = root / insight_prefix
        if not insight_dir.exists():
            continue
        for index_html in insight_dir.glob("*/*/index.html"):
            rel = index_html.relative_to(root)
            parts = rel.parts[:-1]
            if not _is_city_level_path(parts):
                continue
            legacy, canonical = _legacy_to_canonical(parts)  # type: ignore[arg-type]
            if legacy in seen:
                continue
            seen.add(legacy)
            mappings.append(
                {
                    "legacy_url": legacy,
                    "canonical_url": canonical,
                    "state_slug": parts[1],
                    "city_slug": parts[2],
                    "tab": INSIGHT_PREFIX_TO_TAB[parts[0]],
                }
            )

    mappings.sort(key=lambda row: row["legacy_url"])
    return mappings


def write_redirects(mappings: List[Dict[str, str]], out_path: Path) -> None:
    lines = [
        f"{m['legacy_url']} {m['canonical_url']} 301"
        for m in mappings
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate city URL migration mappings.")
    parser.add_argument(
        "--output-json",
        default="data/city_url_migration_map.json",
        help="Output path for JSON migration map.",
    )
    parser.add_argument(
        "--output-redirects",
        default="_deploy/city_redirects_301.txt",
        help="Output path for plain-text redirect rules.",
    )
    args = parser.parse_args()

    mappings = build_city_migration_map(ROOT)

    out_json = ROOT / args.output_json
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"mappings": mappings}, indent=2), encoding="utf-8")

    out_redirects = ROOT / args.output_redirects
    out_redirects.parent.mkdir(parents=True, exist_ok=True)
    write_redirects(mappings, out_redirects)

    print(f"Generated {len(mappings)} city URL mappings")
    print(f"JSON: {out_json}")
    print(f"Redirects: {out_redirects}")


if __name__ == "__main__":
    main()
