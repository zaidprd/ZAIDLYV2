"""Parse the sentinel-delimited article output from the model.

Robust by design: splits on `<<<SECTION>>>` markers (see prompt_builder
OUTPUT_SECTIONS), tolerates a missing trailing <<<END>>>, ignores unknown
markers, and never raises — missing sections come back as empty strings.
"""
import re

from .prompt_builder import OUTPUT_SECTIONS

_MARKER = re.compile(r"<<<([A-Z_]+)>>>")


def parse_article_output(raw):
    """Return a dict with one key per OUTPUT_SECTION (empty string if absent)."""
    out = {name: "" for name in OUTPUT_SECTIONS}
    if not raw:
        return out

    # Find every marker and slice the text between consecutive markers.
    matches = list(_MARKER.finditer(raw))
    for i, m in enumerate(matches):
        name = m.group(1)
        if name == "END":
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        value = raw[start:end].strip()
        if name in out:
            out[name] = value
    return out


def slugify(text, max_len=80):
    slug = (text or "").lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")[:max_len]


def count_words(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(text.split())
