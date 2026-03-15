# one_button_daily.py
# One-button daily run for DataByArea (Android-friendly).
#
# Does (in order):
#  1) Runs make-site.py (publishes today's batch + ensures hubs/legal + updates sitemap/robots)
#  2) Optionally runs relink_existing_pages.py (if present)
#  3) Optionally runs auto_clean_site.py (if present) to move obvious junk to _trash/
#  4) Builds a Cloudflare-ready ZIP (excludes junk + _trash + existing zips)
#  5) Writes a run log so you don't run twice in one day by accident (UTC)
#
# Usage:
#   python one_button_daily.py
#   python one_button_daily.py --relink
#   python one_button_daily.py --clean
#   python one_button_daily.py --relink --clean
#   python one_button_daily.py --force
#
# Output:
#   _deploy/databyarea-deploy-YYYY-MM-DD.zip

import argparse
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RUN_LOG = Path(".daily_runs.json")
MAKE_SITE = Path("make-site.py")
RELINK = Path("relink_existing_pages.py")
CLEANER = Path("auto_clean_site.py")

DEPLOY_DIR = Path("_deploy")
DEPLOY_DIR.mkdir(exist_ok=True)

# Exclusion rules for the deploy zip
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "_trash",
    "_archive",
    "_deploy",
}

EXCLUDE_PREFIXES = (
    ".trashed-",
)

EXCLUDE_EXTS = (
    ".zip",
    ".7z",
    ".rar",
)

EXCLUDE_FILES = {
    ".DS_Store",
    "Thumbs.db",
}


def utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_run_log() -> dict:
    if RUN_LOG.exists():
        try:
            return json.loads(RUN_LOG.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_run_log(obj: dict) -> None:
    RUN_LOG.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def already_ran_today(log: dict) -> bool:
    return log.get("last_run_utc") == utc_date_str()


def run_cmd(cmd: list[str]) -> int:
    print("\n$ " + " ".join(cmd))
    try:
        p = subprocess.run(cmd, check=False)
        return int(p.returncode)
    except FileNotFoundError:
        print("Command not found:", cmd[0])
        return 127


def ensure_file_exists(path: Path, label: str) -> None:
    if not path.exists():
        print(f"ERROR: {label} not found: {path}")
        sys.exit(1)


def should_exclude(rel_path: str) -> bool:
    rel = rel_path.replace(os.sep, "/")
    base = os.path.basename(rel)

    for pfx in EXCLUDE_PREFIXES:
        if base.startswith(pfx):
            return True

    if base in EXCLUDE_FILES:
        return True

    _, ext = os.path.splitext(base.lower())
    if ext in EXCLUDE_EXTS:
        return True

    parts = rel.split("/")
    if parts and parts[0] in EXCLUDE_DIRS:
        return True

    return False


def build_deploy_zip(zip_path: Path) -> tuple[int, int]:
    file_count = 0
    skipped = 0

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("."):
            rel_root = os.path.relpath(root, ".")
            if rel_root == ".":
                rel_root = ""

            # prune excluded dirs
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(rel_root, d))]

            for fname in files:
                rel_path = os.path.join(rel_root, fname) if rel_root else fname
                if should_exclude(rel_path):
                    skipped += 1
                    continue
                zf.write(rel_path, arcname=rel_path)
                file_count += 1

    return file_count, skipped


def main():
    ap = argparse.ArgumentParser(description="One-button daily run: publish + (optional) relink/clean + deploy zip")
    ap.add_argument("--relink", action="store_true", help="Run relink_existing_pages.py after make-site.py (if present).")
    ap.add_argument("--clean", action="store_true", help="Run auto_clean_site.py (if present).")
    ap.add_argument("--force", action="store_true", help="Run even if already ran today (UTC).")
    args = ap.parse_args()

    ensure_file_exists(MAKE_SITE, "Generator (make-site.py)")

    log = load_run_log()
    if already_ran_today(log) and not args.force:
        print(f"Looks like you already ran today (UTC: {utc_date_str()}).")
        print("Use --force to run again.")
        return

    # 1) Run generator
    rc = run_cmd([sys.executable, str(MAKE_SITE)])
    if rc != 0:
        print(f"make-site.py exited with code {rc}. Stopping.")
        sys.exit(rc)

    # 2) Optional: relink
    relink_rc = None
    if args.relink:
        if RELINK.exists():
            relink_rc = run_cmd([sys.executable, str(RELINK)])
            if relink_rc != 0:
                print(f"Warning: relink_existing_pages.py exited with code {relink_rc}. Continuing.")
        else:
            print("Note: relink_existing_pages.py not found; skipping relink.")

    # 3) Optional: clean
    clean_rc = None
    if args.clean:
        if CLEANER.exists():
            clean_rc = run_cmd([sys.executable, str(CLEANER)])
            if clean_rc != 0:
                print(f"Warning: auto_clean_site.py exited with code {clean_rc}. Continuing.")
        else:
            print("Note: auto_clean_site.py not found; skipping clean.")

    # 4) Build deploy zip
    date = utc_date_str()
    zip_path = DEPLOY_DIR / f"databyarea-deploy-{date}.zip"
    if zip_path.exists():
        n = 2
        while True:
            candidate = DEPLOY_DIR / f"databyarea-deploy-{date}__{n}.zip"
            if not candidate.exists():
                zip_path = candidate
                break
            n += 1

    files_added, files_skipped = build_deploy_zip(zip_path)
    print(f"\n📦 Deploy zip created: {zip_path.as_posix()}")
    print(f"   Added files: {files_added}")
    print(f"   Skipped files: {files_skipped}")

    # 5) Write run log
    log["last_run_utc"] = date
    log.setdefault("history", [])
    log["history"].append({
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "relink": bool(args.relink),
        "clean": bool(args.clean),
        "relink_rc": relink_rc,
        "clean_rc": clean_rc,
        "zip": zip_path.as_posix(),
        "python": sys.version.split()[0],
    })
    if len(log["history"]) > 200:
        log["history"] = log["history"][-200:]
    save_run_log(log)

    print("\n✅ All done.")
    print("Next (Cloudflare): Pages → Create project → Upload assets → upload the zip above.")


if __name__ == "__main__":
    main()
