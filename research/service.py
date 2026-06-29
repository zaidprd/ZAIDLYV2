"""Research service — picks the configured provider, runs research, and persists
the result as a ContentBrief (reusable knowledge base).
"""
from decouple import config

from .base import ResearchError, ResearchResult

_FIELDS = [
    'search_intent', 'intent_note', 'competitors', 'headings', 'people_also_ask',
    'related_searches', 'entities', 'lsi_keywords', 'faq', 'content_gap',
    'recommended_word_count', 'internal_link_opportunities',
    'external_reference_opportunities', 'ai_overview_opportunity',
    'provider', 'model_used', 'tokens_in', 'tokens_out', 'cost_usd', 'duration_ms', 'raw',
]


def get_provider(name=None):
    name = name or config('RESEARCH_PROVIDER', default='llm')
    if name == 'llm':
        from .providers.llm import LLMResearchProvider
        return LLMResearchProvider()
    raise ResearchError(f"Unknown RESEARCH_PROVIDER: {name!r}")


def run_research(keyword, *, project=None, user=None, language=None, model=None, save=True):
    """Run research for a keyword. Returns a ContentBrief (saved) or ResearchResult."""
    language = language or (project.language if project else 'id')
    result = get_provider().research(keyword, language=language, model=model)
    if not save:
        return result

    from .models import ContentBrief
    data = {f: getattr(result, f) for f in _FIELDS}
    return ContentBrief.objects.create(
        project=project,
        user=user or (project.user if project else None),
        keyword=keyword,
        language=language,
        **data,
    )


def get_or_create_brief(keyword, *, project=None, user=None, language='id',
                        max_age_days=30, model=None):
    """Return a cached fresh ContentBrief for the keyword, else research it once.
    Avoids spending AI tokens re-researching the same keyword."""
    import datetime
    from django.utils import timezone

    brief = latest_brief(keyword, language=language, project=project)
    if brief and (max_age_days <= 0 or
                  brief.created_at >= timezone.now() - datetime.timedelta(days=max_age_days)):
        return brief                                   # cache hit
    return run_research(keyword, project=project, user=user, language=language, model=model)


def latest_brief(keyword, language='id', project=None):
    """Return the most recent stored brief for a keyword (knowledge-base reuse)."""
    from .models import ContentBrief
    qs = ContentBrief.objects.filter(keyword=keyword, language=language)
    if project is not None:
        qs = qs.filter(project=project)
    return qs.first()
