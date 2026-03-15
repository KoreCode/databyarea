# ensure_index_everywhere.py
# Ensures every directory has an index.html with useful data.
# Safe to run repeatedly. Never overwrites existing index.html.

import os
from datetime import datetime

SITE_NAME = "DataByArea"
SITE_URL = "https://databyarea.com"
CSS_PATH = "/assets/styles.css"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    "_trash",
    "_archive",
    "_deploy",
    "node_modules",
}

HTML_TEMPLATE = (
    "<!doctype html>\n"
    "<html lang=\"en\">\n"
    "<head>\n"
    "  <meta charset=\"utf-8\">\n"
    "  <title>{title}</title>\n"
    "  <meta name=\"description\" content=\"{description}\">\n"
    "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
    "  <link rel=\"canonical\" href=\"{canonical}\">\n"
    "  <link rel=\"stylesheet\" href=\"{css}\">\n"
    "</head>\n"
    "<body>\n"
    "  <div class=\"container\">\n"
    "    <h1>{heading}</h1>\n"
    "    <p class=\"lede\">{description}</p>\n"
    "    {links}\n"
    "    <p><a href=\"/\">Back to home</a></p>\n"
    "    <p><em>Last updated: {date}</em></p>\n"
    "  </div>\n"
    "</body>\n"
    "</html>\n"
)

def should_skip(path):
    return any(part in SKIP_DIRS for part in path.split(os.sep))

def prettify(text):
    return text.replace("-", " ").replace("_", " ").title()

def collect_links(root):
    items = []

    try:
        entries = sorted(os.listdir(root))
    except Exception:
        return ""

    for name in entries:
        if name.startswith("."):
            continue

        full = os.path.join(root, name)

        if os.path.isdir(full) and name not in SKIP_DIRS:
            href = "/" + os.path.relpath(full, ".").replace(os.sep, "/") + "/"
            items.append((prettify(name), href))

        elif name.endswith(".html") and name != "index.html":
            href = "/" + os.path.relpath(full, ".").replace(os.sep, "/").replace(".html", "/")
            items.append((prettify(name.replace(".html", "")), href))

    if not items:
        return ""

    li = "\n".join(f"<li><a href=\"{h}\">{t}</a></li>" for t, h in items)
    return (
        "<h2>Browse</h2>\n"
        "<ul class=\"gridList\">\n"
        f"{li}\n"
        "</ul>\n"
    )

def main():
    created = 0
    today = datetime.utcnow().strftime("%Y-%m-%d")

    for root, dirs, files in os.walk("."):
        if should_skip(root):
            continue

        if root == "." or "index.html" in files:
            continue

        rel = os.path.relpath(root, ".")
        heading = prettify(rel)
        title = f"{heading} | {SITE_NAME}"
        canonical = f"{SITE_URL}/{rel.replace(os.sep, '/')}/"
        description = f"Browse pages and data for {heading}. Updated regularly."

        links = collect_links(root)

        html = HTML_TEMPLATE.format(
            title=title,
            description=description,
            canonical=canonical,
            heading=heading,
            links=links,
            css=CSS_PATH,
            date=today,
        )

        index_path = os.path.join(root, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Created index.html -> {index_path}")
        created += 1

    print(f"\nDone. Created {created} index.html files.")

if __name__ == "__main__":
    main()