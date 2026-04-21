#!/usr/bin/env python3
"""Fail if git conflict markers are present in tracked files."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")
SKIP_DIRS = {".git", "__pycache__"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".zip", ".pack", ".idx", ".rev"}


def tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(p) for p in out.decode("utf-8", errors="ignore").split("\0") if p]


def is_skipped(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    return path.suffix.lower() in SKIP_SUFFIXES


def main() -> int:
    offenders: list[str] = []
    for path in tracked_files():
        if is_skipped(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            if line.startswith(MARKERS):
                offenders.append(f"{path}:{i}:{line[:32]}")

    if offenders:
        print("Found unresolved merge conflict markers:", file=sys.stderr)
        for entry in offenders:
            print(f"  - {entry}", file=sys.stderr)
        return 1

    print("No merge conflict markers found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
