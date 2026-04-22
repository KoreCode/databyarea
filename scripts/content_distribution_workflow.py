#!/usr/bin/env python3
"""Automate content calendar, templated article drafts, social repurposing, and publish queue."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "data" / "content_ops_config.json"
DEFAULT_BRIEFS = REPO_ROOT / "data" / "content_briefs.json"
OUTPUT_DIR = REPO_ROOT / "_deploy" / "content_ops"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "untitled"


def render_template(template: str, context: dict[str, Any]) -> str:
    rendered = template
    for key, val in context.items():
        rendered = rendered.replace("{{" + key + "}}", str(val))
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description="Automate content and distribution workflows.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to content operations config JSON.")
    parser.add_argument("--briefs", default=str(DEFAULT_BRIEFS), help="Path to content briefs JSON.")
    parser.add_argument("--days", type=int, default=14, help="Days of calendar entries to create (default: 14).")
    parser.add_argument("--start-date", default=None, help="ISO start date (YYYY-MM-DD). Defaults to today UTC.")
    args = parser.parse_args()

    config = load_json(Path(args.config), {})
    briefs = load_json(Path(args.briefs), [])

    if not isinstance(config, dict):
        raise SystemExit("Invalid content config JSON format.")
    if not isinstance(briefs, list) or not briefs:
        raise SystemExit("No content briefs found. Add entries to data/content_briefs.json.")

    templates = config.get("templates", {})
    channels = config.get("distribution_channels", ["x", "linkedin", "facebook"]) 
    cadence = config.get("publishing", {}).get("articles_per_day", 1)
    times = config.get("publishing", {}).get("publish_times_utc", ["14:00"])

    article_template = str(templates.get("article_body", "# {{title}}\n\n{{summary}}"))
    social_template = str(
        templates.get(
            "social_post",
            "{{hook}}\n\n{{cta}}\nRead: https://databyarea.com/{{slug}}/",
        )
    )

    start = date.fromisoformat(args.start_date) if args.start_date else datetime.now(timezone.utc).date()

    calendar_entries: list[dict[str, Any]] = []
    articles: list[dict[str, Any]] = []
    social_posts: list[dict[str, Any]] = []
    publish_queue: list[dict[str, Any]] = []

    brief_count = len(briefs)
    for day_offset in range(args.days):
        publish_date = start + timedelta(days=day_offset)
        for slot in range(max(1, cadence)):
            brief = briefs[(day_offset * max(1, cadence) + slot) % brief_count]
            title = str(brief.get("title", "Untitled"))
            slug = str(brief.get("slug") or slugify(title))
            section = str(brief.get("section", "guides"))
            summary = str(brief.get("summary", ""))
            primary_keyword = str(brief.get("primary_keyword", title))
            target_audience = str(brief.get("target_audience", "US budget planners"))
            hook = str(brief.get("social_hook", f"Planning around {primary_keyword}?"))
            cta = str(brief.get("cta", "Compare local costs in minutes."))
            selected_time = times[slot % len(times)]

            context = {
                "title": title,
                "slug": slug,
                "summary": summary,
                "primary_keyword": primary_keyword,
                "target_audience": target_audience,
                "publish_date": publish_date.isoformat(),
                "section": section,
                "hook": hook,
                "cta": cta,
            }

            article_body = render_template(article_template, context)
            article = {
                "title": title,
                "slug": slug,
                "section": section,
                "publish_date_utc": publish_date.isoformat(),
                "publish_time_utc": selected_time,
                "template_source": "data/content_ops_config.json",
                "draft_markdown": article_body,
            }
            articles.append(article)

            calendar_entries.append(
                {
                    "date_utc": publish_date.isoformat(),
                    "time_utc": selected_time,
                    "title": title,
                    "slug": slug,
                    "section": section,
                    "workflow": ["draft", "review", "social", "schedule"],
                }
            )

            publish_queue.append(
                {
                    "url_path": f"/{section}/{slug}/",
                    "status": "scheduled",
                    "publish_at_utc": f"{publish_date.isoformat()}T{selected_time}:00+00:00",
                    "source": "content_distribution_workflow",
                }
            )

            for channel in channels:
                social_posts.append(
                    {
                        "channel": channel,
                        "slug": slug,
                        "publish_date_utc": publish_date.isoformat(),
                        "post": render_template(social_template, context),
                    }
                )

    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "generated_at_utc": generated_at,
        "config_path": str(Path(args.config).relative_to(REPO_ROOT)),
        "briefs_path": str(Path(args.briefs).relative_to(REPO_ROOT)),
        "calendar": calendar_entries,
        "articles": articles,
        "social_posts": social_posts,
        "publish_queue": publish_queue,
    }

    save_json(OUTPUT_DIR / "content_ops_bundle.json", payload)
    save_json(OUTPUT_DIR / "content_calendar.json", calendar_entries)
    save_json(OUTPUT_DIR / "article_drafts.json", articles)
    save_json(OUTPUT_DIR / "social_posts.json", social_posts)
    save_json(OUTPUT_DIR / "publish_queue.json", publish_queue)

    md_lines = [
        "# Content Operations Automation",
        "",
        f"- Generated at (UTC): `{generated_at}`",
        f"- Calendar days: `{args.days}`",
        f"- Articles drafted: `{len(articles)}`",
        f"- Social posts generated: `{len(social_posts)}`",
        f"- Scheduled publish items: `{len(publish_queue)}`",
        "",
        "## First 7 Calendar Entries",
    ]
    for entry in calendar_entries[:7]:
        md_lines.append(f"- `{entry['date_utc']} {entry['time_utc']}` — {entry['title']} ({entry['url_path'] if 'url_path' in entry else '/' + entry['section'] + '/' + entry['slug'] + '/'})")

    (OUTPUT_DIR / "content_ops_summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Generated content automation bundle at: {OUTPUT_DIR}")
    print(f"Articles drafted: {len(articles)}")
    print(f"Social posts generated: {len(social_posts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
