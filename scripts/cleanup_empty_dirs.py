#!/usr/bin/env python3
"""Remove empty directories outside protected paths."""

from pathlib import Path

PROTECTED = {".git", "_deploy", "assets", "data", "scripts"}


def main() -> None:
    removed = 0
    for path in sorted(Path('.').rglob('*'), reverse=True):
        if not path.is_dir():
            continue
        if any(part in PROTECTED for part in path.parts):
            continue
        try:
            next(path.iterdir())
            continue
        except StopIteration:
            path.rmdir()
            removed += 1
            print(f"Removed empty dir: {path}")
        except Exception:
            continue
    print(f"Done. Removed {removed} empty directories.")


if __name__ == '__main__':
    main()
