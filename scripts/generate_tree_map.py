#!/usr/bin/env python3
"""Generate a clean repository tree map markdown file."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "DIRECTORY_TREE.md"
MAX_DEPTH = 3
SKIP_DIRS = {".git", "__pycache__", "node_modules", "_deploy", ".mypy_cache", ".pytest_cache"}


def include(path: Path) -> bool:
    return not any(part in SKIP_DIRS for part in path.parts)


def walk(path: Path, depth: int = 0):
    if depth > MAX_DEPTH:
        return
    entries = sorted([p for p in path.iterdir() if include(p)], key=lambda p: (p.is_file(), p.name.lower()))
    for entry in entries:
        rel = entry.relative_to(ROOT).as_posix()
        prefix = "  " * depth + "- "
        if entry.is_dir():
            yield f"{prefix}`{rel}/`"
            yield from walk(entry, depth + 1)
        else:
            yield f"{prefix}`{rel}`"


def main() -> None:
    lines = [
        "# Repository Tree Map",
        "",
        "Generated clean tree map (depth <= 3, noisy/build dirs excluded).",
        "",
    ]
    lines.extend(walk(ROOT, 0))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
