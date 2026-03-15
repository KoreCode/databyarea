import os
import shutil

# ======================================================
# AUTO CLEAN (PARANOID SAFE)
# - Moves junk into _trash/ (never deletes)
# - NEVER moves any directory that contains index.html
# - DRY_RUN shows what would happen first
# ======================================================

DRY_RUN = True   # <-- run once as True, then switch to False to apply
TRASH_DIR = "_trash"

# Files we always keep (root-level)
KEEP_FILES = {
    "index.html",
    "make-site.py",
    "makesitemap.py",
    "published_manifest.json",
    "sitemap.xml",
    "robots.txt",
    "relink_existing_pages.py",
    "scan_and_cleanup.py",
    "auto_clean_site.py",
    "list_site_tree.py",
}

# Directories we always keep (root-level)
KEEP_DIRS = {
    "assets",
    "data",
    "about",
    "contact",
    "privacy",
    "privacy-policy",
    "terms",
    "scripts",     # keep for now; you can move manually later if desired
    TRASH_DIR,
}

# Exact filenames you said are junk/test (safe to move)
EXACT_JUNK_FILES = {
    "Gen-OLD.py",
    "List.py",
    "newfile.py",
    "Generate-DataByArea",
}

# Extensions that are always junk for deployment
JUNK_EXTS = {".zip", ".7z"}

# Android trash files start with this
TRASH_PREFIX = ".trashed-"


def ensure_trash_dir():
    if not os.path.exists(TRASH_DIR):
        os.makedirs(TRASH_DIR, exist_ok=True)


def safe_move(src_path):
    """Move to _trash/, avoiding name collisions."""
    ensure_trash_dir()
    base = os.path.basename(src_path)
    dst_path = os.path.join(TRASH_DIR, base)

    if os.path.abspath(src_path) == os.path.abspath(dst_path):
        return None  # already in trash

    # avoid collisions
    if os.path.exists(dst_path):
        name, ext = os.path.splitext(base)
        n = 2
        while True:
            candidate = os.path.join(TRASH_DIR, f"{name}__{n}{ext}")
            if not os.path.exists(candidate):
                dst_path = candidate
                break
            n += 1

    if DRY_RUN:
        return dst_path

    shutil.move(src_path, dst_path)
    return dst_path


def dir_has_index_html(dir_path):
    """If a directory contains index.html, it's real content. Never move it."""
    return os.path.isfile(os.path.join(dir_path, "index.html"))


def should_move_file(filename):
    if filename in KEEP_FILES:
        return False
    if filename in EXACT_JUNK_FILES:
        return True
    if filename.startswith(TRASH_PREFIX):
        return True
    ext = os.path.splitext(filename)[1].lower()
    if ext in JUNK_EXTS:
        return True
    return False


def should_move_dir(dirname, full_path):
    # Never touch protected dirs
    if dirname in KEEP_DIRS:
        return False

    # If it contains index.html it is a real page folder (keep)
    if dir_has_index_html(full_path):
        return False

    # Otherwise: we STILL do not auto-move random dirs.
    # This prevents accidental removal of special folders.
    return False


def main():
    ensure_trash_dir()

    moved = []
    skipped = []

    items = sorted(os.listdir("."))

    for name in items:
        if name in (".", ".."):
            continue

        full_path = os.path.join(".", name)

        # FILES
        if os.path.isfile(full_path):
            if should_move_file(name):
                dst = safe_move(full_path)
                moved.append((name, dst))
            else:
                skipped.append(name)

        # DIRECTORIES
        elif os.path.isdir(full_path):
            # Paranoid: do not auto-move directories at all unless you later choose to.
            if should_move_dir(name, full_path):
                dst = safe_move(full_path)
                moved.append((name + "/", dst))
            else:
                skipped.append(name + "/")

    print("\n=== AUTO CLEAN RESULTS ===")
    print("Mode:", "DRY RUN (preview only)" if DRY_RUN else "APPLIED (moved to _trash/)")

    if moved:
        print("\nMoved (or would move):")
        for src, dst in moved:
            print(f" - {src}  ->  {dst}")
    else:
        print("\nNothing to move.")

    print("\nNOTES:")
    print(" - This script NEVER moves any folder containing index.html.")
    print(" - This script does NOT auto-move directories at all (extra safe).")
    print(" - To apply changes, set DRY_RUN = False and run again.\n")


if __name__ == "__main__":
    main()