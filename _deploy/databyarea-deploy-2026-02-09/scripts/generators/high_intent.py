import csv
import json
from datetime import date

from .registry import register
from .utils import make_key, norm


def money(n: int) -> str:
    return "${:,.0f}".format(n)


def faq_jsonld(title: str, faqs: list[dict]) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["q"],
                "acceptedAnswer": {"@type": "Answer", "text": f["a"]},
            }
            for f in faqs
        ],
    }
    return json.dumps(data, ensure_ascii=False)


def make_faqs(service: str, unit: str, low: int, high: int, avg: int):
    return [
        {
            "q": f"How much does a {service.lower()} usually cost?",
            "a": f"Typical {service.lower()} pricing ranges from {money(low)} to {money(high)} per {unit}, with a national average around {money(avg)}."
        },
        {
            "q": "Why do prices vary so much by state?",
            "a": "Labor demand, licensing requirements, cost of living, permit fees, and local competition all affect pricing."
        },
        {
            "q": "How can I get an accurate local estimate?",
            "a": "Get 2–3 written quotes, confirm scope in writing, and ask whether permits, disposal, and materials are included."
        },
        {
            "q": "What should be included in a quote?",
            "a": "Scope, labor and material breakdown, timeline, warranty details, and the payment schedule."
        }
    ]


def build_mdx(row: dict) -> str:
    today = date.today().isoformat()

    slug = row["slug"].strip().strip("/")
    title = row.get("title", "").strip() or slug.replace("-", " ").title()
    h1 = row.get("h1", "").strip() or title

    service = row.get("service", "").strip() or "Service"
    unit = row.get("unit", "").strip() or "unit"

    low = int(row.get("low", 0) or 0)
    high = int(row.get("high", 0) or 0)
    avg = int(row.get("national_avg", 0) or 0)

    cta_text = row.get("cta_text", "").strip() or "Get local quotes"
    cta_url = row.get("cta_url", "").strip() or "/get-quotes"

    related1 = row.get("related_slug1", "").strip()
    related2 = row.get("related_slug2", "").strip()

    faqs = make_faqs(service, unit, low, high, avg)
    faq_ld = faq_jsonld(title, faqs)

    related_links = []
    if related1:
        related_links.append(f"- [{related1.replace('-', ' ').title()}](/" + related1 + ")")
    if related2:
        related_links.append(f"- [{related2.replace('-', ' ').title()}](/" + related2 + ")")
    related_block = "\n".join(related_links) if related_links else "- [Browse more cost guides](/)"

    faq_md = "\n".join([f"### {f['q']}\n{f['a']}\n" for f in faqs])

    return f"""---
title: "{title}"
description: "Updated {today}. Learn typical {service.lower()} pricing by state, what drives costs, and how to get accurate local estimates."
slug: "{slug}"
updated: "{today}"
---

<script type="application/ld+json">{faq_ld}</script>

# {h1}

If you're pricing a project fast, you’re in the right place. Across the U.S., {service.lower()} pricing commonly runs **{money(low)}–{money(high)} per {unit}**, with a national average around **{money(avg)}**.

## Quick cost snapshot
- **Typical range:** {money(low)}–{money(high)} per {unit}
- **National average:** ~{money(avg)} per {unit}
- **Biggest price drivers:** labor rates, permits, availability, and job complexity

## What drives {service.lower()} costs in your area?
1. Labor market + demand
2. Licensing + insurance requirements
3. Permits and inspection fees
4. Materials and travel distance
5. Scope clarity

## Best next step
[{cta_text}]({cta_url})

## Related high-intent guides
{related_block}

---

## FAQ
{faq_md}
"""


@register("high_intent")
def generate(config: dict) -> list[dict]:
    gen_cfg = config["generators"]["high_intent"]
    input_csv = gen_cfg["input_csv"]

    ops: list[dict] = []
    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug = norm(row.get("slug", ""))
            if not slug:
                continue

            # Recommended: include "topic" in CSV. Fallback to slug if missing.
            topic = norm(row.get("topic") or slug)

            key = make_key("high_intent", topic, "us")
            out_path = f"{slug}.mdx"  # root routes: /<slug>

            ops.append({
                "key": key,
                "path": out_path,
                "content": build_mdx({**row, "slug": slug}),
                "meta": {
                    "page_type": "high_intent",
                    "topic": topic,
                    "location": "us",
                    "slug": slug,
                    "title": (row.get("title") or "").strip()
                }
            })

    return ops