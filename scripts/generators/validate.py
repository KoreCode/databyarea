from collections import defaultdict
from .utils import norm

class ValidationError(Exception):
    pass

def validate_high_intent(csv_rows: list[dict]):
    """
    Rules:
    - slug must be present and unique
    - topic must be present (topic column recommended) and unique
      (if topic missing, slug is used as topic)
    """
    seen_slugs = set()
    seen_topics = set()
    errors = []

    for i, row in enumerate(csv_rows, start=1):
        slug = norm(row.get("slug"))
        topic = norm(row.get("topic") or slug)

        if not slug:
            errors.append(f"Row {i}: missing slug")
            continue

        if slug in seen_slugs:
            errors.append(f"Row {i}: duplicate slug '{slug}'")
        seen_slugs.add(slug)

        if not topic:
            errors.append(f"Row {i}: missing topic (and slug could not be used)")
        elif topic in seen_topics:
            errors.append(f"Row {i}: duplicate topic '{topic}'")
        seen_topics.add(topic)

    if errors:
        raise ValidationError("\n".join(errors))