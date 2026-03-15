import os
import shutil

# ============================
# CONFIG
# ============================
ARCHIVE_DIR = "_archive"
DRY_RUN = True   # <-- set to False when ready

KEEP_FILES = {
    "make-site.py",
    "relink_existing_pages.py",
    "makesitemap.py",
    "published_manifest.json",
    "sitemap.xml",
    "robots.txt",
    "index.html",
}

KEEP_DIRS = {
    "data",
    "_archive",
}

KEEP_EXTENSIONS = {
    ".html",     # content pages
}

ARCHIVE_EXTENSIONS = {
    ".zip",
    ".7z",
}

ARCHIVE_NAME_HINTS = {
    "old",
    "gen-old",
    "generate",
    "backup",
}

# ============================
# HELPERS
# ============================
def ensure_archive():
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)

def should_archive_file(fname):
    if fname in KEEP_FILES:
        return False
    ext = os.path.splitext(fname)[1].lower()
    if ext in ARCHIVE_EXTENSIONS:
        return True
    for hint in ARCHIVE_NAME_HINTS:
        if hint in fname.lower():
            return True
    return False

def should_archive_dir(dname):
    if dname in KEEP_DIRS:
        return False
    # content directories have index.html inside
    if os.path.exists(os.path.join(dname, "index.html")):
        return False
    return True

# ============================
# MAIN
# ============================
def main():
    ensure_archive()
    actions = []

    for item in os.listdir("."):
        if item.startswith("."):
            continue

        path = os.path.join(".", item)

        # FILES
        if os.path.isfile(path):
            if should_archive_file(item):
                actions.append(("FILE", item))
                if not DRY_RUN:
                    shutil.move(path, os.path.join(ARCHIVE_DIR, item))

        # DIRECTORIES
        elif os.path.isdir(path):
            if should_archive_dir(item):
                actions.append(("DIR", item))
                if not DRY_RUN:
                    shutil.move(path, os.path.join(ARCHIVE_DIR, item))

    print("\n=== SCAN RESULTS ===")
    if not actions:
        print("✔ No cleanup needed. Directory is already clean.")
        return

    for kind, name in actions:
        print(f"{kind}: {name}")

    print("\n=== MODE ===")
    print("DRY RUN" if DRY_RUN else "CHANGES APPLIED")

    if DRY_RUN:
        print("\nNothing was moved. Set DRY_RUN = False to apply cleanup.")

if __name__ == "__main__":
    main()