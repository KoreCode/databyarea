#!/usr/bin/env python3
"""Build a grouped Markdown documentation index."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "DOCUMENTATION_INDEX.md"
DOC_EXTENSIONS = {".md", ".MD"}
SKIP_DIRS = {
    ".git",
    ".agents",
    ".codex",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "_deploy",
    "_trash",
    "service-guides",
}

CATEGORY_LABELS = {
    "readme": "README Files",
    "ops": "Operations Docs",
    "docs": "Planning And Technical Docs",
    "templates": "Template Docs",
}


def ascii_title(text: str) -> str:
    replacements = {
        "\u2192": "->",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("ascii", errors="ignore").decode("ascii").strip()


def include(path: Path) -> bool:
    return path.is_file() and path.suffix in DOC_EXTENSIONS and not any(part in SKIP_DIRS for part in path.parts)


def category(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    name = path.name.lower()
    if name.startswith("readme"):
        return "readme"
    if rel.startswith("canonical-templates/"):
        return "templates"
    if rel.startswith("docs/"):
        return "docs"
    return "ops"


def title_for(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            clean = line.strip().lstrip("#").strip()
            if clean:
                return ascii_title(clean)
    except Exception:
        pass
    return path.stem.replace("-", " ").replace("_", " ").title()


def main() -> None:
    docs = [path for path in sorted(ROOT.rglob("*")) if include(path)]
    grouped: dict[str, list[Path]] = {key: [] for key in CATEGORY_LABELS}
    for path in docs:
        if path == OUT:
            continue
        grouped.setdefault(category(path), []).append(path)

    lines = [
        "# Documentation Index",
        "",
        "Generated inventory of tracked Markdown documentation for admin review and PR hygiene.",
        "",
        f"Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "Admin backend access:",
        "- `GET /api/docs` lists Markdown documentation.",
        "- `GET /api/doc?path=README.md` returns one Markdown file.",
        "- Legacy README-compatible aliases remain available at `/api/readmes` and `/api/readme?path=...`.",
        "",
    ]

    for key, label in CATEGORY_LABELS.items():
        items = grouped.get(key, [])
        lines.extend([f"## {label}", ""])
        if not items:
            lines.extend(["No files indexed.", ""])
            continue
        for path in items:
            rel = path.relative_to(ROOT).as_posix()
            lines.append(f"- [{title_for(path)}](../{rel}) - `{rel}`")
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT).as_posix()} with {sum(len(v) for v in grouped.values())} Markdown file(s)")


if __name__ == "__main__":
    main()
