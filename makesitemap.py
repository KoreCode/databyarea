import os
from datetime import date

BASE_DIR = "/storage/emulated/0/databyarea-site"
SITE = "https://databyarea.com"
TODAY = date.today().isoformat()

STATES = [
("alabama","Alabama"),("alaska","Alaska"),("arizona","Arizona"),("arkansas","Arkansas"),
("california","California"),("colorado","Colorado"),("connecticut","Connecticut"),("delaware","Delaware"),
("florida","Florida"),("georgia","Georgia"),("hawaii","Hawaii"),("idaho","Idaho"),
("illinois","Illinois"),("indiana","Indiana"),("iowa","Iowa"),("kansas","Kansas"),
("kentucky","Kentucky"),("louisiana","Louisiana"),("maine","Maine"),("maryland","Maryland"),
("massachusetts","Massachusetts"),("michigan","Michigan"),("minnesota","Minnesota"),("mississippi","Mississippi"),
("missouri","Missouri"),("montana","Montana"),("nebraska","Nebraska"),("nevada","Nevada"),
("new-hampshire","New Hampshire"),("new-jersey","New Jersey"),("new-mexico","New Mexico"),("new-york","New York"),
("north-carolina","North Carolina"),("north-dakota","North Dakota"),("ohio","Ohio"),("oklahoma","Oklahoma"),
("oregon","Oregon"),("pennsylvania","Pennsylvania"),("rhode-island","Rhode Island"),("south-carolina","South Carolina"),
("south-dakota","South Dakota"),("tennessee","Tennessee"),("texas","Texas"),("utah","Utah"),
("vermont","Vermont"),("virginia","Virginia"),("washington","Washington"),("west-virginia","West Virginia"),
("wisconsin","Wisconsin"),("wyoming","Wyoming")
]

CATEGORIES = [
("cost-of-living","Cost of Living"),
("utility-costs","Utility Costs"),
("property-taxes","Property Tax Rates"),
("insurance-costs","Insurance Costs")
]

def url_entry(path, priority="0.6", changefreq="weekly"):
    loc = f"{SITE}{path}"
    return f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{TODAY}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>"""

def build_urls():
    urls = []

    # homepage
    urls.append(url_entry("/", priority="1.0", changefreq="weekly"))

    # category hubs
    for cat_slug, _ in CATEGORIES:
        urls.append(url_entry(f"/{cat_slug}/", priority="0.9", changefreq="weekly"))

    # state pages under each category
    for cat_slug, _ in CATEGORIES:
        for state_slug, _ in STATES:
            urls.append(url_entry(f"/{cat_slug}/{state_slug}/", priority="0.7", changefreq="monthly"))

    return urls

def write_sitemap():
    urls = build_urls()
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
""" + "\n".join(urls) + """
</urlset>
"""
    out_path = os.path.join(BASE_DIR, "sitemap.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml)
    print("WROTE:", out_path)

def write_robots():
    txt = f"""User-agent: *
Allow: /

Sitemap: {SITE}/sitemap.xml
"""
    out_path = os.path.join(BASE_DIR, "robots.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("WROTE:", out_path)

def main():
    write_sitemap()
    write_robots()
    print("DONE: sitemap.xml + robots.txt")

main()