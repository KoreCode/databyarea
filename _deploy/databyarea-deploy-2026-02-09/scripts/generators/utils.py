import re

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