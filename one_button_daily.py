# one_button_daily_v2.py
# One-button daily run for DataByArea with "what changed" summary.
#
# Does (in order):
#  0) OPTIONAL: Publish a safe batch of popular city pages (runs publish_popular_cities_daily.py if present)
#  1) Runs make-site.py (publishes today's service pages + ensures hubs/legal)
#  2) OPTIONAL: Runs relink_existing_pages.py
#  3) OPTIONAL: Runs auto_clean_site.py
#  4) Rebuilds sitemap.xml by scanning the filesystem (includes city pages)
#  5) Updates robots.txt
#  6) Builds a Cloudflare-ready ZIP (excludes junk)
#  7) Prints a "what changed" summary (new URLs + counts)
#
# Usage:
#   python one_button_daily_v2.py
#   python one_button_daily_v2.py --cities 10
#   python one_button_daily_v2.py --cities 10 --relink --clean
#   python one_button_daily_v2.py --force
#
# Output:
#   _deploy/databyarea-deploy-YYYY-MM-DD.zip

import argparse
import json
import os
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

SITE_URL = "https://databyarea.com"

RUN_LOG = Path(".daily_runs.json")
MAKE_SITE = Path("make-site.py")
RELINK = Path("relink_existing_pages.py")
CLEANER = Path("auto_clean_site.py")
POPULAR_CITIES_PUBLISHER = Path("publish_popular_cities_daily.py")

MANIFEST_PATH = Path("published_manifest.json")
SITEMAP_PATH = Path("sitemap.xml")
ROBOTS_PATH = Path("robots.txt")

DEPLOY_DIR = Path("_deploy")
DEPLOY_DIR.mkdir(exist_ok=True)

# Exclusion rules for scan + zip
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "_trash",
    "_archive",
    "_deploy",
}
EXCLUDE_PREFIXES = (".trashed-",)
EXCLUDE_EXTS = (".zip", ".7z", ".rar")
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}

def utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def already_ran_today(log: dict) -> bool:
    return log.get("last_run_utc") == utc_date_str()

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

def run_cmd_capture(cmd: list[str]) -> tuple[int, str]:
    print("\n$ " + " ".join(cmd))
    try:
        p = subprocess.run(cmd, check=False, capture_output=True, text=True)
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        if out.strip():
            print(out.strip())
        return int(p.returncode), out
    except FileNotFoundError:
        print("Command not found:", cmd[0])
        return 127, ""

def ensure_file_exists(path: Path, label: str) -> None:
    if not path.exists():
        print(f"ERROR: {label} not found: {path}")
        sys.exit(1)

def parse_created_urls(output: str) -> list[str]:
    # expects lines like: Created: /section/state/city/
    created = []
    for line in output.splitlines():
        line = line.strip()
        if line.lower().startswith("created: /"):
            created.append(line.split("Created:", 1)[1].strip())
    return created

def scan_all_index_pages() -> list[str]:
    # Returns list of URL paths for every index.html in the site (excluding skipped dirs/files)
    url_paths = []
    for root, dirs, files in os.walk("."):
        rel_root = os.path.relpath(root, ".")
        if rel_root == ".":
            rel_root = ""
        # prune excluded dirs
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(rel_root, d))]
        if "index.html" in files:
            if should_exclude(os.path.join(rel_root, "index.html")):
                continue
            if rel_root:
                url_paths.append("/" + rel_root.replace(os.sep, "/").strip("/") + "/")
            else:
                url_paths.append("/")  # home
    # de-dup + stable sort (shorter first)
    url_paths = sorted(set(url_paths), key=lambda x: (x.count("/"), x))
    return url_paths

def rebuild_sitemap_from_filesystem() -> int:
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    today = datetime.utcnow().strftime("%Y-%m-%d")

    urls = scan_all_index_pages()
    for path in urls:
        u = ET.SubElement(urlset, "url")
        ET.SubElement(u, "loc").text = urljoin(SITE_URL.rstrip("/") + "/", path.lstrip("/"))
        ET.SubElement(u, "lastmod").text = today

    ET.ElementTree(urlset).write(SITEMAP_PATH, encoding="utf-8", xml_declaration=True)
    return len(urls)

def update_robots():
    ROBOTS_PATH.write_text(
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE_URL.rstrip('/')}/{SITEMAP_PATH.name}\n",
        encoding="utf-8",
    )

def build_deploy_zip(zip_path: Path) -> tuple[int, int]:
    file_count = 0
    skipped = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("."):
            rel_root = os.path.relpath(root, ".")
            if rel_root == ".":
                rel_root = ""
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(rel_root, d))]
            for fname in files:
                rel_path = os.path.join(rel_root, fname) if rel_root else fname
                if should_exclude(rel_path):
                    skipped += 1
                    continue
                zf.write(rel_path, arcname=rel_path)
                file_count += 1
    return file_count, skipped

def diff_manifest(before: dict, after: dict) -> list[str]:
    b = set((before.get("published") or {}).keys())
    a = set((after.get("published") or {}).keys())
    new = sorted(a - b)
    return new

def main():
    ap = argparse.ArgumentParser(description="One-button daily run with summary + deploy zip.")
    ap.add_argument("--cities", type=int, default=10, help="How many popular city pages to publish today (default 10).")
    ap.add_argument("--no-cities", action="store_true", help="Skip city publishing even if script exists.")
    ap.add_argument("--relink", action="store_true", help="Run relink_existing_pages.py after make-site.py (if present).")
    ap.add_argument("--clean", action="store_true", help="Run auto_clean_site.py (if present).")
    ap.add_argument("--force", action="store_true", help="Run even if already ran today (UTC).")
    args = ap.parse_args()

    ensure_file_exists(MAKE_SITE, "Generator (make-site.py)")

    log = load_json(RUN_LOG, {})
    if already_ran_today(log) and not args.force:
        print(f"Looks like you already ran today (UTC: {utc_date_str()}). Use --force to run again.")
        return

    # Track changes
    before_manifest = load_json(MANIFEST_PATH, {"published": {}})
    before_urls = set(scan_all_index_pages())

    created_city_urls = []
    city_rc = None

    # 0) Popular cities publish (optional)
    if (not args.no_cities) and POPULAR_CITIES_PUBLISHER.exists() and args.cities > 0:
        city_rc, city_out = run_cmd_capture([sys.executable, str(POPULAR_CITIES_PUBLISHER), "--max", str(args.cities)])
        if city_rc != 0:
            print(f"Warning: publish_popular_cities_daily.py exited with code {city_rc}. Continuing.")
        created_city_urls = parse_created_urls(city_out)
    else:
        print("\n(Skipping popular cities publish.)")

    # 1) Run make-site
    make_rc, make_out = run_cmd_capture([sys.executable, str(MAKE_SITE)])
    if make_rc != 0:
        print(f"make-site.py exited with code {make_rc}. Stopping.")
        sys.exit(make_rc)

    # 2) Optional: relink
    relink_rc = None
    if args.relink:
        if RELINK.exists():
            relink_rc, _ = run_cmd_capture([sys.executable, str(RELINK)])
            if relink_rc != 0:
                print(f"Warning: relink_existing_pages.py exited with code {relink_rc}. Continuing.")
        else:
            print("Note: relink_existing_pages.py not found; skipping relink.")

    # 3) Optional: clean
    clean_rc = None
    if args.clean:
        if CLEANER.exists():
            clean_rc, _ = run_cmd_capture([sys.executable, str(CLEANER)])
            if clean_rc != 0:
                print(f"Warning: auto_clean_site.py exited with code {clean_rc}. Continuing.")
        else:
            print("Note: auto_clean_site.py not found; skipping clean.")

    # 4-5) Rebuild sitemap + robots from filesystem (includes city pages)
    total_sitemap_urls = rebuild_sitemap_from_filesystem()
    update_robots()

    # 6) Build deploy zip
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

    # Change summary
    after_manifest = load_json(MANIFEST_PATH, {"published": {}})
    after_urls = set(scan_all_index_pages())

    new_manifest_slugs = diff_manifest(before_manifest, after_manifest)
    new_url_paths = sorted(after_urls - before_urls)

    # 7) Log
    log["last_run_utc"] = date
    log.setdefault("history", [])
    log["history"].append({
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "cities": (0 if args.no_cities else int(args.cities)),
        "city_rc": city_rc,
        "make_rc": make_rc,
        "relink": bool(args.relink),
        "relink_rc": relink_rc,
        "clean": bool(args.clean),
        "clean_rc": clean_rc,
        "sitemap_urls": total_sitemap_urls,
        "zip": zip_path.as_posix(),
        "python": sys.version.split()[0],
        "new_manifest_slugs": len(new_manifest_slugs),
        "new_url_paths": len(new_url_paths),
    })
    if len(log["history"]) > 200:
        log["history"] = log["history"][-200:]
    save_json(RUN_LOG, log)

    # Print "what changed"
    print("\n==============================")
    print("WHAT CHANGED TODAY")
    print("==============================")
    if created_city_urls:
        print(f"Popular city pages created (from internal list): {len(created_city_urls)}")
        for u in created_city_urls[:25]:
            print("  + " + u)
        if len(created_city_urls) > 25:
            print(f"  ... and {len(created_city_urls) - 25} more")
    else:
        print("Popular city pages created: 0")

    if new_manifest_slugs:
        print(f"New service/system pages added to manifest: {len(new_manifest_slugs)}")
        for s in new_manifest_slugs[:25]:
            print("  + /" + s.strip("/") + "/")
        if len(new_manifest_slugs) > 25:
            print(f"  ... and {len(new_manifest_slugs) - 25} more")
    else:
        print("New service/system pages added to manifest: 0")

    # new URL paths discovered by filesystem scan (includes city pages + hubs)
    if new_url_paths:
        print(f"New index pages found on disk: {len(new_url_paths)}")
        for p in new_url_paths[:25]:
            print("  + " + p)
        if len(new_url_paths) > 25:
            print(f"  ... and {len(new_url_paths) - 25} more")
    else:
        print("New index pages found on disk: 0")

    print("\nSitemap URLs total:", total_sitemap_urls)
    print("Deploy zip:", zip_path.as_posix())
    print(f"Zip contents -> Added files: {files_added} | Skipped: {files_skipped}")
    print("\nNext (Cloudflare): Pages -> Upload assets -> upload the zip above.")
    print("==============================\n")

if __name__ == "__main__":
    main()
