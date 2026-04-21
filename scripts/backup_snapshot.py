#!/usr/bin/env python3
"""Create operational backups for DataByArea.

Backs up key automation files and optionally the generated site directory into a
timestamped tar.gz archive under _deploy/backups.
"""

from __future__ import annotations

import argparse
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = REPO_ROOT / "_deploy" / "backups"

INCLUDE_PATHS = [
    Path("scripts"),
    Path("assets"),
    Path("admin_backend.py"),
    Path("one_button_daily.py"),
    Path("run_daily.sh"),
    Path("setup_autorun.sh"),
    Path("README.md"),
    Path("monetization_flags.json"),
    Path("published_manifest.json"),
    Path("data/published_manifest.json"),
]


def prune_old_backups(retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    for backup in BACKUP_DIR.glob("databyarea-backup-*.tar.gz"):
        try:
            if datetime.fromtimestamp(backup.stat().st_mtime, tz=timezone.utc) < cutoff:
                backup.unlink()
                removed += 1
        except FileNotFoundError:
            continue
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a backup snapshot for DataByArea operations.")
    parser.add_argument("--include-site", action="store_true", help="Include generated site/ directory in backup")
    parser.add_argument("--retention-days", type=int, default=21, help="Delete backups older than N days")
    args = parser.parse_args()

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = BACKUP_DIR / f"databyarea-backup-{stamp}.tar.gz"

    paths = list(INCLUDE_PATHS)
    if args.include_site:
        paths.append(Path("site"))

    added: list[str] = []
    with tarfile.open(archive_path, mode="w:gz") as tar:
        for rel in paths:
            source = REPO_ROOT / rel
            if not source.exists():
                continue
            tar.add(source, arcname=str(rel))
            added.append(str(rel))

    removed = prune_old_backups(args.retention_days)
    print(f"backup_created={archive_path}")
    print(f"files_included={len(added)}")
    if added:
        print("included_paths=" + ",".join(added))
    print(f"old_backups_removed={removed}")


if __name__ == "__main__":
    main()
