# one_button_daily_v2.py
# One-button daily run for DataByArea with "what changed" summary.
#
# Does (in order):
#  0) OPTIONAL: Ensure missing state index pages exist (runs scripts/ensure_states.py if present)
#  1) OPTIONAL: Publish a safe batch of popular city pages (runs publish_popular_cities_daily.py if present)
#  1) Runs the single canonical generator:
#       scripts/build_site.py
#  1) Runs the first available generator:
#       make-site.py OR scripts/build_site.py OR newfile.py
#     (publishes today's service pages + ensures hubs/legal)
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
SINGLE_GENERATOR = Path("scripts/build_site.py")
GENERATOR_CANDIDATES = [
    Path("make-site.py"),
    Path("scripts/build_site.py"),
    Path("newfile.py"),
]
RELINK = Path("relink_existing_pages.py")
CLEANER = Path("auto_clean_site.py")
EMPTY_DIR_CLEANER = Path("scripts/cleanup_empty_dirs.py")
POPULAR_CITIES_PUBLISHER = Path("publish_popular_cities_daily.py")
STATE_ENSURER = Path("scripts/ensure_states.py")

MANIFEST_PATH = Path("published_manifest.json")
SITEMAP_PATH = Path("sitemap.xml")
SITEMAPS_DIR = Path("sitemaps")
SITEMAP_SEGMENTS = ("states", "counties", "cities", "services")
ROBOTS_PATH = Path("robots.txt")

DEPLOY_DIR = Path("_deploy")
DEPLOY_DIR.mkdir(exist_ok=True)
RUN_SUMMARY_JSON = DEPLOY_DIR / "last_daily_run_summary.json"
RUN_SUMMARY_MD = DEPLOY_DIR / "last_daily_run_summary.md"
VERSION_JSON = Path("assets/site-version.json")
VERSION_FOOTER_JS = Path("assets/version-footer.js")
VERSION_SCRIPT_TAG = '<script defer src="/assets/version-footer.js"></script>'

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
STATE_SLUGS = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
    "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
    "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new-hampshire", "new-jersey", "new-mexico",
    "new-york", "north-carolina", "north-dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode-island", "south-carolina", "south-dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west-virginia", "wisconsin", "wyoming", "district-of-columbia",
}

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

def write_run_summary(summary: dict) -> None:
    save_json(RUN_SUMMARY_JSON, summary)
    lines = [
        "# Daily Runner Summary",
        "",
        f"- Date (UTC): `{summary.get('date_utc')}`",
        f"- Generator: `{summary.get('generator')}`",
        f"- City pages created: `{summary.get('created_city_urls_count')}`",
        f"- New manifest slugs: `{summary.get('new_manifest_slugs_count')}`",
        f"- New index pages: `{summary.get('new_url_paths_count')}`",
        f"- Sitemap URLs total: `{summary.get('sitemap_urls_total')}`",
        f"- Sitemap segment counts: `{summary.get('sitemap_segment_counts')}`",
        f"- Deploy zip: `{summary.get('deploy_zip')}`",
        "",
        "## Return Codes",
        f"- city publisher: `{summary.get('city_rc')}`",
        f"- generator: `{summary.get('make_rc')}`",
        f"- relink: `{summary.get('relink_rc')}`",
        f"- clean: `{summary.get('clean_rc')}`",
    ]
    RUN_SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

def git_commit_short() -> str:
    rc, out = run_cmd_capture(["git", "rev-parse", "--short", "HEAD"])
    if rc == 0 and out.strip():
        return out.strip().splitlines()[-1].strip()
    return "unknown"

def ensure_version_footer_js() -> None:
    VERSION_FOOTER_JS.parent.mkdir(parents=True, exist_ok=True)
    if VERSION_FOOTER_JS.exists():
        return
    VERSION_FOOTER_JS.write_text(
        """(function () {\n"""
        """  const root = document.createElement('div');\n"""
        """  root.id = 'site-version-footer';\n"""
        """  root.style.cssText = 'position:fixed;bottom:8px;right:8px;background:#111;color:#fff;font:12px/1.2 Arial,sans-serif;padding:6px 8px;border-radius:8px;opacity:.82;z-index:99999';\n"""
        """  fetch('/assets/site-version.json', { cache: 'no-store' })\n"""
        """    .then(r => r.ok ? r.json() : null)\n"""
        """    .then(v => {\n"""
        """      if (!v) return;\n"""
        """      root.textContent = `v ${v.commit_short || 'unknown'} · ${v.updated_utc || ''}`;\n"""
        """      document.body.appendChild(root);\n"""
        """    })\n"""
        """    .catch(() => {});\n"""
        """})();\n""",
        encoding="utf-8",
    )

def inject_version_script_into_html() -> int:
    added = 0
    for root, dirs, files in os.walk("."):
        rel_root = os.path.relpath(root, ".")
        if rel_root == ".":
            rel_root = ""
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(rel_root, d))]
        if "index.html" not in files:
            continue
        html_path = Path(root) / "index.html"
        txt = html_path.read_text(encoding="utf-8", errors="ignore")
        if VERSION_SCRIPT_TAG in txt:
            continue
        if "</body>" in txt:
            txt = txt.replace("</body>", f"  {VERSION_SCRIPT_TAG}\n</body>")
        else:
            txt += "\n" + VERSION_SCRIPT_TAG + "\n"
        html_path.write_text(txt, encoding="utf-8")
        added += 1
    return added

def maybe_update_site_version_for_autorun(summary: dict) -> None:
    if os.getenv("DBA_AUTORUN", "").strip() != "1":
        print("Skipping version stamp update (DBA_AUTORUN is not set to 1).")
        return
    VERSION_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "commit_short": git_commit_short(),
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "services_requested": summary.get("services_requested"),
        "cities_requested": summary.get("cities_requested"),
        "deploy_zip": summary.get("deploy_zip"),
    }
    VERSION_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Updated version stamp: {VERSION_JSON}")

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

def run_cmd_capture(cmd: list[str], env: dict | None = None) -> tuple[int, str]:
    print("\n$ " + " ".join(cmd))
    try:
        p = subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        if out.strip():
            print(out.strip())
        return int(p.returncode), out
    except FileNotFoundError:
        print("Command not found:", cmd[0])
        return 127, ""

def resolve_generator() -> Path:
    if SINGLE_GENERATOR.exists():
        return SINGLE_GENERATOR
    print("ERROR: Required generator script not found.")
    print(f"Expected: {SINGLE_GENERATOR}")
    for candidate in GENERATOR_CANDIDATES:
        if candidate.exists():
            return candidate
    checked = ", ".join(str(p) for p in GENERATOR_CANDIDATES)
    print("ERROR: No generator script found.")
    print(f"Checked: {checked}")
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

def rebuild_sitemap_from_filesystem() -> dict[str, int]:
    def classify_sitemap_segment(path: str) -> str:
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return "services"
        if parts[0] in {"state", "states"}:
            if len(parts) <= 2:
                return "states"
            if len(parts) == 3:
                return "counties"
            return "cities"
        if len(parts) >= 2 and parts[1] in STATE_SLUGS:
            if len(parts) == 2:
                return "states"
            if len(parts) == 3:
                return "counties"
            return "cities"
        return "services"

    def write_urlset(path: Path, url_paths: list[str], today_str: str) -> None:
        urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for url_path in url_paths:
            u = ET.SubElement(urlset, "url")
            ET.SubElement(u, "loc").text = urljoin(SITE_URL.rstrip("/") + "/", url_path.lstrip("/"))
            ET.SubElement(u, "lastmod").text = today_str
        ET.ElementTree(urlset).write(path, encoding="utf-8", xml_declaration=True)

    def url_to_index_file(url_path: str) -> Path:
        if url_path == "/":
            return Path("index.html")
        return Path(url_path.strip("/")) / "index.html"

    def validate_sitemaps(segment_paths: dict[str, Path]) -> None:
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        missing: list[str] = []
        for xml_path in segment_paths.values():
            root = ET.parse(xml_path).getroot()
            for loc in root.findall("sm:url/sm:loc", ns):
                loc_text = (loc.text or "").strip()
                if not loc_text.startswith(SITE_URL):
                    continue
                rel = "/" + loc_text.replace(SITE_URL.rstrip("/"), "", 1).lstrip("/")
                if not url_to_index_file(rel).exists():
                    missing.append(rel)
        if missing:
            raise RuntimeError(
                "Sitemap integrity check failed. Missing index.html for: "
                + ", ".join(sorted(set(missing))[:20])
            )

    today = datetime.utcnow().strftime("%Y-%m-%d")
    urls = scan_all_index_pages()
    segments: dict[str, list[str]] = {name: [] for name in SITEMAP_SEGMENTS}
    for path in urls:
        segments[classify_sitemap_segment(path)].append(path)

    SITEMAPS_DIR.mkdir(parents=True, exist_ok=True)
    segment_paths: dict[str, Path] = {}
    for name in SITEMAP_SEGMENTS:
        seg_path = SITEMAPS_DIR / f"{name}.xml"
        segment_paths[name] = seg_path
        write_urlset(seg_path, sorted(set(segments[name])), today)

    index_root = ET.Element("sitemapindex", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for name in SITEMAP_SEGMENTS:
        sm = ET.SubElement(index_root, "sitemap")
        ET.SubElement(sm, "loc").text = f"{SITE_URL.rstrip('/')}/{(SITEMAPS_DIR / f'{name}.xml').as_posix()}"
        ET.SubElement(sm, "lastmod").text = today
    ET.ElementTree(index_root).write(SITEMAP_PATH, encoding="utf-8", xml_declaration=True)

    validate_sitemaps(segment_paths)
    counts = {name: len(set(segments[name])) for name in SITEMAP_SEGMENTS}
    counts["total"] = sum(counts.values())
    return counts

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
    ap.add_argument("--services", type=int, default=1, help="How many new service slugs to publish today (default 1).")
    ap.add_argument("--no-cities", action="store_true", help="Skip city publishing even if script exists.")
    ap.add_argument("--relink", action="store_true", help="Run relink_existing_pages.py after make-site.py (if present).")
    ap.add_argument("--clean", action="store_true", help="Run auto_clean_site.py (if present).")
    ap.add_argument("--force", action="store_true", help="Run even if already ran today (UTC).")
    args = ap.parse_args()

    generator = resolve_generator()
    print(f"Using generator: {generator}")

    log = load_json(RUN_LOG, {})
    if already_ran_today(log) and not args.force:
        print(f"Looks like you already ran today (UTC: {utc_date_str()}). Use --force to run again.")
        return

    # Track changes
    before_manifest = load_json(MANIFEST_PATH, {"published": {}})
    before_urls = set(scan_all_index_pages())

    created_city_urls = []
    city_rc = None
    states_rc = None

    # 0) Ensure state pages (optional)
    if STATE_ENSURER.exists():
        states_rc, _ = run_cmd_capture([sys.executable, str(STATE_ENSURER)])
        if states_rc != 0:
            print(f"Warning: {STATE_ENSURER} exited with code {states_rc}. Continuing.")
    else:
        print("\n(State ensurer not found; skipping state-page check.)")

    # 1) Popular cities publish (optional)
    if (not args.no_cities) and POPULAR_CITIES_PUBLISHER.exists() and args.cities > 0:
        city_rc, city_out = run_cmd_capture([sys.executable, str(POPULAR_CITIES_PUBLISHER), "--max", str(args.cities), "--force"])
        if city_rc != 0:
            print(f"Warning: publish_popular_cities_daily.py exited with code {city_rc}. Continuing.")
        created_city_urls = parse_created_urls(city_out)
    else:
        print("\n(Skipping popular cities publish.)")

    # 2) Run generator
    cmd = [sys.executable, str(generator)]
    if args.services > 0 and generator.as_posix() == "scripts/build_site.py":
        cmd.extend(["--daily-max", str(args.services)])
    env = os.environ.copy()
    env["DBA_DAILY_MAX"] = str(max(1, int(args.services)))
    make_rc, make_out = run_cmd_capture(cmd, env=env)
    if make_rc != 0:
        print(f"{generator} exited with code {make_rc}. Stopping.")
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
        if EMPTY_DIR_CLEANER.exists():
            _, _ = run_cmd_capture([sys.executable, str(EMPTY_DIR_CLEANER)])

    # 4-5) Rebuild sitemap + robots from filesystem (includes city pages)
    sitemap_counts = rebuild_sitemap_from_filesystem()
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
    summary = {
        "date_utc": date,
        "generator": str(generator),
        "cities_requested": (0 if args.no_cities else int(args.cities)),
        "services_requested": int(args.services),
        "created_city_urls_count": len(created_city_urls),
        "created_city_urls": created_city_urls,
        "new_manifest_slugs_count": len(new_manifest_slugs),
        "new_manifest_slugs": new_manifest_slugs,
        "new_url_paths_count": len(new_url_paths),
        "new_url_paths": new_url_paths,
        "sitemap_urls_total": sitemap_counts["total"],
        "sitemap_segment_counts": sitemap_counts,
        "deploy_zip": zip_path.as_posix(),
        "zip_files_added": files_added,
        "zip_files_skipped": files_skipped,
        "city_rc": city_rc,
        "states_rc": states_rc,
        "make_rc": make_rc,
        "relink_rc": relink_rc,
        "clean_rc": clean_rc,
    }
    write_run_summary(summary)
    ensure_version_footer_js()
    injected = inject_version_script_into_html()
    maybe_update_site_version_for_autorun(summary)

    # 7) Log
    log["last_run_utc"] = date
    log.setdefault("history", [])
    log["history"].append({
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "cities": (0 if args.no_cities else int(args.cities)),
        "city_rc": city_rc,
        "states_rc": states_rc,
        "services": int(args.services),
        "make_rc": make_rc,
        "generator": str(generator),
        "relink": bool(args.relink),
        "relink_rc": relink_rc,
        "clean": bool(args.clean),
        "clean_rc": clean_rc,
        "sitemap_urls": sitemap_counts["total"],
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

    print("\nSitemap URLs total:", sitemap_counts["total"])
    print("Sitemap segment counts:", sitemap_counts)
    print("Deploy zip:", zip_path.as_posix())
    print(f"Zip contents -> Added files: {files_added} | Skipped: {files_skipped}")
    print(f"Version footer script tags injected: {injected}")
    print("Run summary JSON:", RUN_SUMMARY_JSON.as_posix())
    print("Run summary Markdown:", RUN_SUMMARY_MD.as_posix())
    print("\nNext (Cloudflare): Pages -> Upload assets -> upload the zip above.")
    print("==============================\n")

if __name__ == "__main__":
    main()
