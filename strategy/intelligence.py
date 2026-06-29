"""Keyword Intelligence (Engine Batch 3).

Reads DiscoveredKeyword (real data), uses AI to ANALYSE only (cluster, intent,
business value), then computes a deterministic, null-safe priority score. AI
never fabricates volume/CPC/difficulty — those stay None until a data provider.
"""
from django.db.models import Avg

from ai_service import generate, pricing
from research.parsing import extract_json, to_int

from .prompts import build_intelligence_messages

_INTENT_WEIGHT = {
    'transactional': 1.0,
    'commercial': 0.9,
    'informational': 0.6,
    'navigational': 0.4,
}


def _clamp_0_100(value):
    n = to_int(value, 0)
    return max(0, min(100, n))


def compute_priority(business_value, intent, confidence, volume=None, difficulty=None):
    """Null-safe priority: works without volume/difficulty; uses them if present."""
    bv = (business_value or 0) / 100.0
    iw = _INTENT_WEIGHT.get((intent or '').lower(), 0.6)
    score = (0.6 * bv + 0.3 * iw + 0.1 * (confidence or 0)) * 100

    if volume:  # only when real data exists
        score *= min(1.5, 1 + (volume / 10000))
    if difficulty is not None:
        score *= max(0.5, 1 - (difficulty / 200))
    return round(score, 2)


def _business_context(project):
    analysis = project.analyses.first()  # latest BusinessAnalysis if any
    if analysis:
        parts = [analysis.summary]
        if analysis.offerings:
            parts.append("Produk/jasa: " + ", ".join(map(str, analysis.offerings)))
        if analysis.themes:
            parts.append("Tema: " + ", ".join(map(str, analysis.themes)))
        return "\n".join(p for p in parts if p)
    return f"{project.business_description}\nNiche: {project.niche}".strip()


def analyze_keywords(project, *, model=None, save=True):
    """Cluster + intent + business value + priority for a project's keywords."""
    from .models import DiscoveredKeyword, TopicCluster

    keywords = list(DiscoveredKeyword.objects.filter(project=project))
    if not keywords:
        return {'clusters': 0, 'keywords': 0}

    # normalize + dedup index (case-insensitive)
    index = {}
    for kw in keywords:
        index.setdefault(kw.keyword.strip().lower(), kw)

    gen = generate(
        build_intelligence_messages(_business_context(project), list(index.keys())),
        model=model, max_tokens=2000, temperature=0.2,
    )
    data = extract_json(gen.text)
    items = data.get('keywords') if isinstance(data.get('keywords'), list) else []

    cluster_cache = {}
    touched = set()
    processed = 0

    for item in items:
        kw_text = str(item.get('keyword', '')).strip().lower()
        dk = index.get(kw_text)
        if not dk:
            continue
        cname = (str(item.get('cluster', '')).strip() or 'Lainnya')[:150]
        intent = str(item.get('intent', '')).strip().lower()
        bv = _clamp_0_100(item.get('business_value'))

        if save:
            cluster = cluster_cache.get(cname.lower())
            if cluster is None:
                cluster, _ = TopicCluster.objects.get_or_create(project=project, name=cname)
                cluster_cache[cname.lower()] = cluster
            dk.cluster = cluster
            touched.add(cluster.id)

        dk.search_intent = intent
        dk.business_value = bv
        dk.priority_score = compute_priority(bv, intent, dk.confidence, dk.volume, dk.difficulty)
        processed += 1

        if save:
            dk.save(update_fields=['cluster', 'search_intent', 'business_value', 'priority_score'])

    # roll up cluster priority = avg of member keyword priorities
    if save:
        for cid in touched:
            cluster = TopicCluster.objects.get(id=cid)
            avg = cluster.keywords.aggregate(p=Avg('priority_score'))['p'] or 0.0
            cluster.priority = round(avg, 2)
            cluster.save(update_fields=['priority'])

    cost = pricing.estimate_text_cost(gen.model, gen.tokens_in, gen.tokens_out)
    return {'clusters': len(touched), 'keywords': processed, 'cost_usd': round(cost, 6)}
