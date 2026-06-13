import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "search-index.json"
CATEGORIES = {
    "cost-of-living": "cost of living",
    "utility-costs": "utility costs",
    "property-taxes": "property taxes",
    "insurance-costs": "insurance costs",
}
SERVICE_GUIDES = {
    "plumber": "plumber rates",
    "electrician": "electrician rates",
    "hvac": "HVAC installation",
    "roofing": "roof replacement",
    "water-heater": "water heater installation",
    "garage-door": "garage door repair",
    "foundation": "foundation repair",
    "concrete-driveway": "concrete driveway cost",
}
SERVICE_PROJECTS = {
    "plumber": {
        "leak-repair": "leak repair",
        "drain-cleaning": "drain cleaning",
        "faucet-replacement": "faucet replacement",
        "pipe-replacement": "pipe replacement",
    },
    "electrician": {
        "new-outlets": "new outlets",
        "panel-upgrade": "panel upgrade",
        "ev-charger-installation": "EV charger installation",
        "light-fixture-installation": "light fixture installation",
    },
    "hvac": {
        "ac-replacement": "AC replacement",
        "furnace-replacement": "furnace replacement",
        "heat-pump-installation": "heat pump installation",
        "ductwork-repair": "ductwork repair",
    },
    "roofing": {
        "asphalt-shingle-replacement": "asphalt shingle replacement",
        "roof-leak-repair": "roof leak repair",
        "flashing-repair": "flashing repair",
        "roof-deck-repair": "roof deck repair",
    },
    "water-heater": {
        "tank-water-heater-replacement": "tank water heater replacement",
        "tankless-water-heater-installation": "tankless water heater installation",
        "expansion-tank-installation": "expansion tank installation",
        "water-heater-code-upgrades": "water heater code upgrades",
    },
    "garage-door": {
        "spring-replacement": "spring replacement",
        "opener-installation": "opener installation",
        "panel-replacement": "panel replacement",
        "full-door-replacement": "full door replacement",
    },
    "foundation": {
        "crack-repair": "foundation crack repair",
        "pier-installation": "pier installation",
        "basement-waterproofing": "basement waterproofing",
        "structural-stabilization": "structural stabilization",
    },
    "concrete-driveway": {
        "driveway-replacement": "driveway replacement",
        "concrete-removal": "concrete removal",
        "stamped-concrete": "stamped concrete",
        "reinforced-driveway": "reinforced driveway",
    },
}
STATE_NAMES = {
    "alabama": ("Alabama", "AL"),
    "alaska": ("Alaska", "AK"),
    "arizona": ("Arizona", "AZ"),
    "arkansas": ("Arkansas", "AR"),
    "california": ("California", "CA"),
    "colorado": ("Colorado", "CO"),
    "connecticut": ("Connecticut", "CT"),
    "delaware": ("Delaware", "DE"),
    "florida": ("Florida", "FL"),
    "georgia": ("Georgia", "GA"),
    "hawaii": ("Hawaii", "HI"),
    "idaho": ("Idaho", "ID"),
    "illinois": ("Illinois", "IL"),
    "indiana": ("Indiana", "IN"),
    "iowa": ("Iowa", "IA"),
    "kansas": ("Kansas", "KS"),
    "kentucky": ("Kentucky", "KY"),
    "louisiana": ("Louisiana", "LA"),
    "maine": ("Maine", "ME"),
    "maryland": ("Maryland", "MD"),
    "massachusetts": ("Massachusetts", "MA"),
    "michigan": ("Michigan", "MI"),
    "minnesota": ("Minnesota", "MN"),
    "mississippi": ("Mississippi", "MS"),
    "missouri": ("Missouri", "MO"),
    "montana": ("Montana", "MT"),
    "nebraska": ("Nebraska", "NE"),
    "nevada": ("Nevada", "NV"),
    "new-hampshire": ("New Hampshire", "NH"),
    "new-jersey": ("New Jersey", "NJ"),
    "new-mexico": ("New Mexico", "NM"),
    "new-york": ("New York", "NY"),
    "north-carolina": ("North Carolina", "NC"),
    "north-dakota": ("North Dakota", "ND"),
    "ohio": ("Ohio", "OH"),
    "oklahoma": ("Oklahoma", "OK"),
    "oregon": ("Oregon", "OR"),
    "pennsylvania": ("Pennsylvania", "PA"),
    "rhode-island": ("Rhode Island", "RI"),
    "south-carolina": ("South Carolina", "SC"),
    "south-dakota": ("South Dakota", "SD"),
    "tennessee": ("Tennessee", "TN"),
    "texas": ("Texas", "TX"),
    "utah": ("Utah", "UT"),
    "vermont": ("Vermont", "VT"),
    "virginia": ("Virginia", "VA"),
    "washington": ("Washington", "WA"),
    "west-virginia": ("West Virginia", "WV"),
    "wisconsin": ("Wisconsin", "WI"),
    "wyoming": ("Wyoming", "WY"),
}


def label_from_slug(slug):
    return " ".join(part.capitalize() for part in slug.split("-"))


def title_case_city(slug):
    return label_from_slug(slug)


def page_exists(*parts):
    return (ROOT.joinpath(*parts) / "index.html").exists()


def add_item(items, seen, item):
    if item["url"] in seen:
        return
    seen.add(item["url"])
    items.append(item)


def state_aliases(name, abbr, category_label=None):
    aliases = [name, abbr, f"{name} data", f"{abbr} data"]
    if category_label:
        aliases.extend([f"{name} {category_label}", f"{abbr} {category_label}"])
    return aliases


def city_aliases(city, state_name, state_abbr, category_label=None):
    aliases = [city, f"{city} {state_abbr}", f"{city} {state_name}"]
    if category_label:
        aliases.extend([f"{city} {category_label}", f"{city} {state_abbr} {category_label}"])
    return aliases


def zip_aliases_for_path(path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    alias_match = re.search(r"aliases\s*:\s*\[[^\]]*?['\"](\d{5}(?:-\d{4})?)['\"]", text, re.I | re.S)
    if alias_match:
        return [alias_match.group(1)]
    zip_match = re.search(r"(?:zip|postal)[^.\n]{0,80}\b(\d{5}(?:-\d{4})?)\b", text, re.I)
    if zip_match:
        return [zip_match.group(1)]
    return []


def city_dirs_for_state(state_slug):
    state_dir = ROOT / state_slug
    if not state_dir.exists():
        return []
    city_dirs = []
    for child in state_dir.iterdir():
        if not child.is_dir() or child.name == "kiester-template":
            continue
        if (child / "index.html").exists():
            city_dirs.append(child)
    return sorted(city_dirs, key=lambda p: p.name)


def build_index():
    items = []
    seen = set()
    state_slugs = sorted(
        slug
        for slug in STATE_NAMES
        if page_exists(slug) or any(page_exists(category, slug) for category in CATEGORIES)
    )

    states = []
    for state_slug in state_slugs:
        state_name, state_abbr = STATE_NAMES[state_slug]
        states.append({"slug": state_slug, "name": state_name, "abbr": state_abbr})

        if page_exists(state_slug):
            add_item(items, seen, {
                "title": f"{state_name} state profile",
                "url": f"/{state_slug}/",
                "type": "State profile",
                "category": "state-profile",
                "state": state_slug,
                "state_name": state_name,
                "state_abbr": state_abbr,
                "aliases": state_aliases(state_name, state_abbr),
            })

        for category, category_label in CATEGORIES.items():
            if page_exists(category, state_slug):
                add_item(items, seen, {
                    "title": f"{state_name} {category_label}",
                    "url": f"/{category}/{state_slug}/",
                    "type": "State insight",
                    "category": category,
                    "state": state_slug,
                    "state_name": state_name,
                    "state_abbr": state_abbr,
                    "aliases": state_aliases(state_name, state_abbr, category_label),
                })

        for city_dir in city_dirs_for_state(state_slug):
            city_slug = city_dir.name
            city = title_case_city(city_slug)
            aliases = city_aliases(city, state_name, state_abbr)
            aliases.extend(zip_aliases_for_path(city_dir / "index.html"))
            add_item(items, seen, {
                "title": f"{city}, {state_abbr}",
                "url": f"/{state_slug}/{city_slug}/",
                "type": "City profile",
                "category": "city-dashboard",
                "state": state_slug,
                "state_name": state_name,
                "state_abbr": state_abbr,
                "city": city_slug,
                "aliases": aliases,
            })

        for category, category_label in CATEGORIES.items():
            category_state_dir = ROOT / category / state_slug
            if not category_state_dir.exists():
                continue
            for city_dir in sorted(category_state_dir.iterdir(), key=lambda p: p.name):
                if not city_dir.is_dir() or not (city_dir / "index.html").exists():
                    continue
                city_slug = city_dir.name
                city = title_case_city(city_slug)
                aliases = city_aliases(city, state_name, state_abbr, category_label)
                aliases.extend(zip_aliases_for_path(city_dir / "index.html"))
                add_item(items, seen, {
                    "title": f"{city} {category_label}",
                    "url": f"/{category}/{state_slug}/{city_slug}/",
                    "type": "City insight",
                    "category": category,
                    "state": state_slug,
                    "state_name": state_name,
                    "state_abbr": state_abbr,
                    "city": city_slug,
                    "aliases": aliases,
                })

    service_root = ROOT / "service-guides"
    if (service_root / "index.html").exists():
        add_item(items, seen, {
            "title": "Service Guide Hub",
            "url": "/service-guides/",
            "type": "Service guide hub",
            "category": "service-guide",
            "aliases": ["service guides", "contractor rates", "project rates", "home service costs"],
        })

    for service_slug, service_label in SERVICE_GUIDES.items():
        if page_exists("service-guides", service_slug):
            add_item(items, seen, {
                "title": label_from_slug(service_label),
                "url": f"/service-guides/{service_slug}/",
                "type": "Service guide",
                "category": "service-guide",
                "service": service_slug,
                "aliases": [service_label, f"{service_label} by state", f"{service_label} near me"],
            })
        for project_slug, project_label in SERVICE_PROJECTS.get(service_slug, {}).items():
            if page_exists("service-guides", service_slug, project_slug):
                add_item(items, seen, {
                    "title": f"{label_from_slug(project_label)} cost",
                    "url": f"/service-guides/{service_slug}/{project_slug}/",
                    "type": "Detailed service guide",
                    "category": "service-guide",
                    "service": service_slug,
                    "project": project_slug,
                    "aliases": [project_label, f"{project_label} cost", f"{service_label} {project_label}"],
                })
        for state_slug, (state_name, state_abbr) in STATE_NAMES.items():
            if page_exists("service-guides", service_slug, state_slug):
                add_item(items, seen, {
                    "title": f"{state_name} {service_label}",
                    "url": f"/service-guides/{service_slug}/{state_slug}/",
                    "type": "State service guide",
                    "category": "service-guide",
                    "service": service_slug,
                    "state": state_slug,
                    "state_name": state_name,
                    "state_abbr": state_abbr,
                    "aliases": [f"{state_name} {service_label}", f"{state_abbr} {service_label}", f"{service_label} {state_name}"],
                })
            for project_slug, project_label in SERVICE_PROJECTS.get(service_slug, {}).items():
                if page_exists("service-guides", service_slug, state_slug, project_slug):
                    add_item(items, seen, {
                        "title": f"{state_name} {project_label} cost",
                        "url": f"/service-guides/{service_slug}/{state_slug}/{project_slug}/",
                        "type": "State detailed service guide",
                        "category": "service-guide",
                        "service": service_slug,
                        "project": project_slug,
                        "state": state_slug,
                        "state_name": state_name,
                        "state_abbr": state_abbr,
                        "aliases": [f"{state_name} {project_label}", f"{state_abbr} {project_label}", f"{project_label} cost {state_name}"],
                    })
            for city_dir in city_dirs_for_state(state_slug):
                city_slug = city_dir.name
                if not page_exists("service-guides", service_slug, state_slug, city_slug):
                    continue
                city = title_case_city(city_slug)
                add_item(items, seen, {
                    "title": f"{city} {service_label}",
                    "url": f"/service-guides/{service_slug}/{state_slug}/{city_slug}/",
                    "type": "City service guide",
                    "category": "service-guide",
                    "service": service_slug,
                    "state": state_slug,
                    "state_name": state_name,
                    "state_abbr": state_abbr,
                    "city": city_slug,
                    "aliases": [f"{city} {service_label}", f"{city} {state_abbr} {service_label}", f"{service_label} {city}"],
                })
                for project_slug, project_label in SERVICE_PROJECTS.get(service_slug, {}).items():
                    if not page_exists("service-guides", service_slug, state_slug, city_slug, project_slug):
                        continue
                    add_item(items, seen, {
                        "title": f"{city} {project_label} cost",
                        "url": f"/service-guides/{service_slug}/{state_slug}/{city_slug}/{project_slug}/",
                        "type": "City detailed service guide",
                        "category": "service-guide",
                        "service": service_slug,
                        "project": project_slug,
                        "state": state_slug,
                        "state_name": state_name,
                        "state_abbr": state_abbr,
                        "city": city_slug,
                        "aliases": [f"{city} {project_label}", f"{city} {state_abbr} {project_label}", f"{project_label} cost {city}"],
                    })

    items.sort(key=lambda item: (item.get("state") or "", item.get("city") or "", item["category"], item["title"]))
    return {"states": states, "items": items}


def main():
    data = build_index()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(data['states'])} states and {len(data['items'])} items")


if __name__ == "__main__":
    main()
