import json
import re
from html import escape
from urllib.parse import urljoin

SITE_NAME = "Data By Area"
SITE_URL = "https://databyarea.com"

def norm(s: str) -> str:
    """Normalize strings for stable keys/paths."""
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")

def make_key(page_type: str, topic: str, location: str) -> str:
    """
    Global uniqueness key:
      page_type::topic::location

    Examples:
      high_intent::electrician-rates::us
      state_topic::electrician-rates::minnesota
      city_topic::electrician-rates::faribault-mn
    """
    return f"{norm(page_type)}::{norm(topic)}::{norm(location)}"


def canonical_url(path: str, site_url: str = SITE_URL) -> str:
    clean = "/" + (path or "").strip("/") + "/"
    return urljoin(site_url.rstrip("/") + "/", clean.lstrip("/"))


def build_seo_payload(
    *,
    path: str,
    title: str,
    description: str,
    page_type: str,
    site_name: str = SITE_NAME,
    site_url: str = SITE_URL,
    image_url: str | None = None,
    updated_iso: str | None = None,
) -> dict:
    canonical = canonical_url(path, site_url=site_url)
    og_type = "article" if page_type in {"state_detail", "service"} else "website"
    return {
        "title": title.strip(),
        "description": description.strip(),
        "canonical": canonical,
        "page_type": page_type,
        "site_name": site_name,
        "og_type": og_type,
        "image_url": image_url or f"{site_url.rstrip('/')}/assets/logo.png",
        "updated_iso": updated_iso or "",
    }


def render_seo_meta_tags(seo: dict) -> str:
    title = escape(seo["title"])
    description = escape(seo["description"])
    canonical = escape(seo["canonical"])
    image_url = escape(seo["image_url"])
    site_name = escape(seo["site_name"])
    og_type = escape(seo["og_type"])
    return (
        f"<title>{title}</title>\n"
        f'<meta name="description" content="{description}">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="robots" content="index,follow,max-image-preview:large">\n'
        f'<link rel="canonical" href="{canonical}">\n'
        f'<meta property="og:type" content="{og_type}">\n'
        f'<meta property="og:site_name" content="{site_name}">\n'
        f'<meta property="og:title" content="{title}">\n'
        f'<meta property="og:description" content="{description}">\n'
        f'<meta property="og:url" content="{canonical}">\n'
        f'<meta property="og:image" content="{image_url}">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:title" content="{title}">\n'
        f'<meta name="twitter:description" content="{description}">\n'
        f'<meta name="twitter:image" content="{image_url}">'
    )


def build_jsonld_blocks(
    *,
    seo: dict,
    page_type: str,
    breadcrumb_items: list[dict] | None = None,
    faq_items: list[dict] | None = None,
) -> list[dict]:
    blocks: list[dict] = [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": seo["title"],
        "description": seo["description"],
        "url": seo["canonical"],
    }]
    if breadcrumb_items:
        blocks.append({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": idx,
                    "name": item["name"],
                    "item": item["url"],
                }
                for idx, item in enumerate(breadcrumb_items, start=1)
            ],
        })
    if page_type == "state_detail":
        blocks.append({
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": seo["title"],
            "description": seo["description"],
            "url": seo["canonical"],
        })
    if faq_items:
        blocks.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq["q"],
                    "acceptedAnswer": {"@type": "Answer", "text": faq["a"]},
                }
                for faq in faq_items
            ],
        })
    return blocks


def render_jsonld_scripts(blocks: list[dict]) -> str:
    return "\n".join(
        f'<script type="application/ld+json">{json.dumps(block, ensure_ascii=False)}</script>'
        for block in blocks
    )
