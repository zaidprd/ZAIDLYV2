"""Defensive JSON extraction for research output (never raises)."""
import json
import re


def extract_json(raw):
    """Return a dict parsed from the model output, or {} on failure.

    Tolerates code fences and surrounding prose by isolating the outermost
    {...} block before parsing.
    """
    if not raw:
        return {}
    text = raw.strip()
    # strip ```json ... ``` fences if present
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except (ValueError, TypeError):
            return {}
    return {}


def to_int(value, default=0):
    if isinstance(value, int):
        return value
    try:
        m = re.search(r"\d+", str(value))
        return int(m.group()) if m else default
    except (ValueError, TypeError):
        return default
