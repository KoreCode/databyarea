#!/usr/bin/env python3
"""Refresh homepage modules from repository data and existing generated pages."""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"
METRICS = [
    ("cost-of-living", "Cost of living", "Compare household budgets and affordability"),
    ("utility-costs", "Utility costs", "Review electric, gas, and water cost guides"),
    ("property-taxes", "Property taxes", "Browse local tax burden and housing levy pages"),
    ("insurance-costs", "Insurance costs", "Compare location-based insurance and risk cost guides"),
]
STATE_TO_ABBR = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar", "california": "ca",
    "colorado": "co", "connecticut": "ct", "delaware": "de", "florida": "fl", "georgia": "ga",
    "hawaii": "hi", "idaho": "id", "illinois": "il", "indiana": "in", "iowa": "ia",
    "kansas": "ks", "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md",
    "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms",
    "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv", "new-hampshire": "nh",
    "new-jersey": "nj", "new-mexico": "nm", "new-york": "ny", "north-carolina": "nc",
    "north-dakota": "nd", "ohio": "oh", "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa",
    "rhode-island": "ri", "south-carolina": "sc", "south-dakota": "sd", "tennessee": "tn",
    "texas": "tx", "utah": "ut", "vermont": "vt", "virginia": "va", "washington": "wa",
    "west-virginia": "wv", "wisconsin": "wi", "wyoming": "wy",
}
ABBR_TO_STATE = {abbr: state for state, abbr in STATE_TO_ABBR.items()}


def slugify(value: str) -> str:
    value = value.strip().lower().replace(".", "")
    value = re.sub(r"&", " and ", value)
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"\s+", "-", value).strip("-")
    return re.sub(r"-{2,}", "-", value)


def normalize_city(value: str) -> str:
    value = value.split(",")[0].strip().lower()
    for suffix in (" city", " town", " village", " borough", " municipality", " cdp"):
        if value.endswith(suffix):
            value = value[: -len(suffix)].strip()
    value = value.replace("saint ", "st ")
    return slugify(value)


def fmt_int(value: int | None) -> str:
    return f"{value:,}" if value is not None else "Population data available"


def title_from_slug(slug: str) -> str:
    small = {"of", "by", "and", "the"}
    words = slug.replace("-", " ").split()
    return " ".join(word if word in small else word.capitalize() for word in words)


def load_city_populations() -> dict[tuple[str, str], int]:
    populations: dict[tuple[str, str], int] = {}
    with (ROOT / "data" / "cities.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            state = (row.get("state_slug") or "").strip().lower()
            state = ABBR_TO_STATE.get(state, state)
            city_key = normalize_city(row.get("city") or "")
            if not state or not city_key:
                continue
            try:
                population = int(float(row.get("population") or 0))
            except ValueError:
                continue
            key = (state, city_key)
            if population > populations.get(key, 0):
                populations[key] = population
    return populations


def existing_index(href: str) -> bool:
    return (ROOT / href.strip("/") / "index.html").exists()


def collect_popular_cities(limit: int = 8) -> list[dict[str, object]]:
    populations = load_city_populations()
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    with (ROOT / "popular_cities.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            state = slugify(row.get("state") or "")
            city_name = (row.get("city") or "").strip()
            city_slug = slugify(city_name)
            key = (state, city_slug)
            if key in seen:
                continue
            href = None
            metric_label = None
            for metric_slug, label, _ in METRICS:
                candidate = f"/{metric_slug}/{state}/{city_slug}/"
                if existing_index(candidate):
                    href = candidate
                    metric_label = label
                    break
            if not href:
                continue
            seen.add(key)
            rows.append({
                "city": city_name,
                "state": title_from_slug(state),
                "population": populations.get(key),
                "href": href,
                "metric": metric_label,
            })
            if len(rows) >= limit:
                break
    return rows


def collect_recent_guides(limit: int = 6) -> list[dict[str, str]]:
    candidates: dict[str, str] = {}
    for path in (ROOT / "published_manifest.json", ROOT / "data" / "published_manifest.json"):
        if not path.exists():
            continue
        payload = json.loads(path.read_text())
        for slug, meta in payload.get("published", {}).items():
            if meta.get("system"):
                continue
            published_at = meta.get("published_at") or ""
            href = f"/{slug}/"
            if existing_index(href) and published_at >= candidates.get(slug, ""):
                candidates[slug] = published_at
    def sort_key(item: tuple[str, str]) -> tuple[str, str]:
        return (item[1], item[0])
    rows = []
    for slug, published_at in sorted(candidates.items(), key=sort_key, reverse=True)[:limit]:
        label = title_from_slug(slug.replace("-by-state", ""))
        try:
            dt = datetime.strptime(published_at, "%Y-%m-%d")
            display_date = dt.strftime("%b %-d, %Y")
        except ValueError:
            display_date = published_at
        rows.append({"title": label, "date": display_date, "href": f"/{slug}/"})
    return rows


def count_metric_pages(metric_slug: str) -> int:
    root = ROOT / metric_slug
    if not root.exists():
        return 0
    return sum(1 for _ in root.glob("**/index.html"))


def collect_metrics() -> list[dict[str, object]]:
    rows = []
    for slug, label, description in METRICS:
        href = f"/{slug}/"
        if not existing_index(href):
            continue
        rows.append({"label": label, "description": description, "count": count_metric_pages(slug), "href": href})
    return rows


def build_section() -> str:
    popular = collect_popular_cities()
    recent = collect_recent_guides()
    metrics = collect_metrics()

    popular_cards = "\n".join(
        f'''          <a class="group rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-md hover:ring-brand-blue" href="{escape(city['href'])}">
            <span class="text-sm font-semibold uppercase tracking-[0.18em] text-brand-blue">{escape(str(city['metric']))}</span>
            <h3 class="mt-3 text-xl font-extrabold text-navy group-hover:text-brand-blue">{escape(str(city['city']))}, {escape(str(city['state']))}</h3>
            <p class="mt-2 text-sm text-slate-600">Population {escape(fmt_int(city['population']))}</p>
            <span class="mt-4 inline-flex font-semibold text-brand-blue">Open local guide →</span>
          </a>'''
        for city in popular
    )
    recent_items = "\n".join(
        f'''          <li class="flex items-center justify-between gap-4 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <div>
              <a class="font-bold text-navy hover:text-brand-blue" href="{escape(row['href'])}">{escape(row['title'])}</a>
              <p class="mt-1 text-sm text-slate-500">Published {escape(row['date'])}</p>
            </div>
            <span class="flex-none text-brand-blue" aria-hidden="true">→</span>
          </li>'''
        for row in recent
    )
    metric_cards = "\n".join(
        f'''          <a class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-md hover:ring-brand-blue" href="{escape(row['href'])}">
            <div class="flex items-start justify-between gap-4">
              <h3 class="text-xl font-extrabold text-navy">{escape(row['label'])}</h3>
              <span class="rounded-full bg-blue-50 px-3 py-1 text-sm font-bold text-blue-700">{row['count']} pages</span>
            </div>
            <p class="mt-3 text-sm text-slate-600">{escape(row['description'])}</p>
            <span class="mt-5 inline-flex font-semibold text-brand-blue">Explore this metric →</span>
          </a>'''
        for row in metrics
    )

    return f'''    <section class="mx-auto max-w-7xl px-5 pb-20 sm:px-6 lg:px-8" aria-labelledby="homepage-data-title">
      <div class="rounded-[2rem] bg-slate-50 p-6 shadow-inner ring-1 ring-slate-200 sm:p-8 lg:p-10">
        <div class="mx-auto max-w-3xl text-center">
          <p class="text-sm font-bold uppercase tracking-[0.24em] text-brand-blue">Live repository data</p>
          <h2 id="homepage-data-title" class="mt-3 text-3xl font-extrabold tracking-tight text-navy sm:text-4xl">Explore current DataByArea guides</h2>
          <p class="mt-4 text-lg text-slate-600">These homepage modules are refreshed from city population data, curated popular cities, publish manifests, and generated guide directories so each link points to a page that exists.</p>
        </div>

        <div class="mt-10">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p class="text-sm font-bold uppercase tracking-[0.18em] text-coral">Popular cities</p>
              <h3 class="mt-2 text-2xl font-extrabold text-navy">Curated city guides with live local pages</h3>
            </div>
            <p class="text-sm text-slate-500">Sourced from <code>popular_cities.csv</code> and <code>data/cities.csv</code>.</p>
          </div>
          <div class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
{popular_cards}
          </div>
        </div>

        <div class="mt-12 grid gap-8 lg:grid-cols-[1fr_1.1fr]">
          <div>
            <p class="text-sm font-bold uppercase tracking-[0.18em] text-coral">Recently updated guides</p>
            <h3 class="mt-2 text-2xl font-extrabold text-navy">Latest published cost resources</h3>
            <p class="mt-3 text-sm text-slate-600">Ordered from the repository publish manifests and filtered to existing guide pages.</p>
            <ul class="mt-5 space-y-3">
{recent_items}
            </ul>
          </div>

          <div>
            <p class="text-sm font-bold uppercase tracking-[0.18em] text-coral">Explore by metric</p>
            <h3 class="mt-2 text-2xl font-extrabold text-navy">Generated coverage by topic</h3>
            <p class="mt-3 text-sm text-slate-600">Counts include every available <code>index.html</code> under each generated metric directory.</p>
            <div class="mt-5 grid gap-4 sm:grid-cols-2">
{metric_cards}
            </div>
          </div>
        </div>
      </div>
    </section>'''


def main() -> None:
    html = INDEX_PATH.read_text()
    section_markers = (
        '    <section class="mx-auto max-w-7xl px-5 pb-20 sm:px-6 lg:px-8" aria-labelledby="homepage-data-title">',
        '    <section class="mx-auto max-w-7xl px-5 pb-20 sm:px-6 lg:px-8" aria-labelledby="regional-insights-title">',
    )
    start = next((html.find(marker) for marker in section_markers if html.find(marker) != -1), -1)
    if start == -1:
        raise RuntimeError("Could not find homepage data section insertion point")
    end = html.index("  </main>", start)
    updated = html[:start] + build_section() + "\n" + html[end:]
    INDEX_PATH.write_text(updated)


if __name__ == "__main__":
    main()
