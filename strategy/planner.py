"""Content Planner (Engine Batch 4).

Takes the best analysed keywords, generates + scores titles (reusing the existing
title generator), and writes ContentPlanItem rows — the reviewable plan. No
Campaign yet, no article generation, no WordPress.
"""
from ai_service import generate
from generator.prompt_builder import build_titles_messages
from generator.tasks import _parse_titles

_POWER_WORDS = ('cara', 'panduan', 'tips', 'terbaik', 'lengkap', 'cek', 'kenali')


def score_title(title, keyword):
    """Deterministic title score (0-1). No AI, no fabricated metrics."""
    t = (title or '').lower()
    kw = (keyword or '').lower()
    score = 0.0
    if kw and kw in t:
        score += 0.5
    length = len(title or '')
    if 40 <= length <= 70:
        score += 0.3
    elif 30 <= length <= 80:
        score += 0.15
    if any(w in t for w in _POWER_WORDS):
        score += 0.2
    return round(min(score, 1.0), 2)


def _select_keywords(project, limit):
    from .models import DiscoveredKeyword
    return list(
        DiscoveredKeyword.objects
        .filter(project=project, business_value__isnull=False)
        .order_by('-priority_score')[:limit]
    )


def build_content_plan(project, *, limit=20, titles_per_kw=5, model=None, save=True):
    """For the top `limit` keywords: generate+score titles, create ContentPlanItem."""
    from .models import ContentPlanItem

    items = []
    for dk in _select_keywords(project, limit):
        messages = build_titles_messages(
            dk.keyword,
            language=project.language,
            tone=project.get_tone_display(),
            target_audience=project.target_audience,
            writing_style=project.writing_style,
            count=titles_per_kw,
        )
        titles = _parse_titles(generate(messages, model=model, max_tokens=500, temperature=0.7).text)
        scored = sorted(((score_title(t, dk.keyword), t) for t in titles), reverse=True)
        best = scored[0][1] if scored else dk.keyword
        alt = [{'title': t, 'score': s} for s, t in scored]

        if save:
            item, _ = ContentPlanItem.objects.update_or_create(
                project=project, keyword=dk,
                defaults=dict(cluster=dk.cluster, chosen_title=best, alt_titles=alt,
                              priority=dk.priority_score, status='planned'),
            )
            items.append(item)

    return items
