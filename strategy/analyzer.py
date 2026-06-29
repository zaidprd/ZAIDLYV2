"""Business Analyzer (Engine Batch 1).

Turns a Business Profile (+ optional homepage text) into a BusinessAnalysis the
discovery pipeline can seed from. AI does analysis only — no fabricated metrics.
"""
from types import SimpleNamespace

from ai_service import generate, pricing
from research.parsing import extract_json

from .prompts import build_analysis_messages
from .fetch import fetch_homepage


def _list(data, key):
    val = data.get(key)
    return val if isinstance(val, list) else []


def analyze_business(project, *, fetch_website=True, model=None, save=True):
    page_text = fetch_homepage(project.website_url) if (fetch_website and project.website_url) else ''

    profile = {
        'name': project.name,
        'website_url': project.website_url,
        'business_description': project.business_description,
        'niche': project.niche,
        'target_country': project.target_country,
        'goal': project.get_goal_display() if project.goal else '',
        'language': project.language,
        'target_audience': project.target_audience,
    }

    gen = generate(build_analysis_messages(profile, page_text), model=model,
                   max_tokens=1500, temperature=0.3)
    data = extract_json(gen.text)
    cost = pricing.estimate_text_cost(gen.model, gen.tokens_in, gen.tokens_out)

    fields = dict(
        summary=str(data.get('summary', '')).strip(),
        offerings=_list(data, 'offerings'),
        themes=_list(data, 'themes'),
        target_audience=str(data.get('target_audience', '')).strip(),
        competitor_hints=_list(data, 'competitor_hints'),
        language=project.language,
        source_url=project.website_url,
        website_fetched=bool(page_text),
        provider='llm',
        model_used=gen.model,
        tokens_in=gen.tokens_in,
        tokens_out=gen.tokens_out,
        cost_usd=round(cost, 6),
        duration_ms=gen.duration_ms,
        raw=data,
    )

    if not save:
        return SimpleNamespace(project=project, **fields)

    from .models import BusinessAnalysis
    return BusinessAnalysis.objects.create(project=project, **fields)
