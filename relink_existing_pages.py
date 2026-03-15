import os
import json
from datetime import datetime

# =========================
# CONFIG
# =========================
MANIFEST_PATH = "published_manifest.json"
QUEUE_FILE = "data/core_pages.txt"
OUTPUT_ROOT = "."
MAX_PAGES_TO_UPDATE = 50   # safety cap per run
DRY_RUN = False            # set True to preview only

# Marker comments — do not change
START_MARKER = "<!-- INTERNAL_LINKS_START -->"
END_MARKER = "<!-- INTERNAL_LINKS_END -->"


# =========================
# HELPERS
# =========================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip().strip("/") for l in f if l.strip() and not l.startswith("#")]

def slug_to_title(slug):
    return slug.replace("-", " ").title()

def build_links(slug, published_slugs):
    """
    Build a small set of links to newer pages
    """
    newer = [s for s in published_slugs if s != slug]
    newer = newer[-6:]  # last 6 published pages

    if not newer:
        return ""

    lis = "\n".join(
        f'<li><a href="/{s}/">{slug_to_title(s)}</a></li>'
        for s in newer
    )

    return f"""
<h2>Related guides</h2>
<ul>
{lis}
</ul>
""".strip()


# =========================
# MAIN RELINK LOGIC
# =========================
def main():
    manifest = load_json(MANIFEST_PATH, {"published": {}})
    published = manifest.get("published", {})

    if not published:
        print("No published pages found.")
        return

    # Order pages by publish date
    ordered = sorted(
        published.items(),
        key=lambda x: x[1].get("published_at", "")
    )
    published_slugs = [s for s, _ in ordered]

    updates = 0

    for slug in published_slugs:
        if updates >= MAX_PAGES_TO_UPDATE:
            break

        index_path = os.path.join(OUTPUT_ROOT, slug, "index.html")
        if not os.path.exists(index_path):
            continue

        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        if START_MARKER not in html or END_MARKER not in html:
            # page not prepared for relinking
            continue

        new_links = build_links(slug, published_slugs)

        block = f"""
{START_MARKER}
{new_links}
{END_MARKER}
""".strip()

        before = html.split(START_MARKER)[0]
        after = html.split(END_MARKER)[-1]

        new_html = before + block + after

        if new_html == html:
            continue

        updates += 1

        if DRY_RUN:
            print(f"[DRY RUN] Would update: {slug}")
        else:
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(new_html)
            print(f"Updated links in: {slug}")

    print(f"Relink pass complete. Pages updated: {updates}")


if __name__ == "__main__":
    main()