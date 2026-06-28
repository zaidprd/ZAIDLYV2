"""HPP (cost-of-goods) analytics from per-job telemetry (PRD §8).

Aggregates the cost telemetry stored on generate jobs so the business can see
real production cost per article. Margin needs a credit selling price (set once
Mayar.id top-up pricing is decided) — surfaced here only when provided.
"""
from django.db.models import Avg, Sum, Count

from queue_manager.models import QueueJob


def hpp_summary(user, credit_price_usd=None):
    """Return cost/quality aggregates over a user's generated articles."""
    jobs = QueueJob.objects.filter(user=user, job_type=QueueJob.TYPE_GENERATE, cost_total_usd__gt=0)
    agg = jobs.aggregate(
        articles=Count('id'),
        total_cost=Sum('cost_total_usd'),
        avg_cost=Avg('cost_total_usd'),
        avg_tokens_in=Avg('tokens_in'),
        avg_tokens_out=Avg('tokens_out'),
        avg_quality=Avg('quality_score'),
        avg_duration_ms=Avg('duration_ms'),
    )

    avg_cost = agg['avg_cost'] or 0.0
    summary = {
        'articles': agg['articles'] or 0,
        'total_cost_usd': round(agg['total_cost'] or 0.0, 4),
        'avg_cost_usd': round(avg_cost, 4),
        'avg_tokens_in': int(agg['avg_tokens_in'] or 0),
        'avg_tokens_out': int(agg['avg_tokens_out'] or 0),
        'avg_quality': round(agg['avg_quality'] or 0, 1),
        'avg_duration_s': round((agg['avg_duration_ms'] or 0) / 1000, 1),
        'margin_pct': None,
    }

    # Margin only computable when a selling price per article is known.
    if credit_price_usd and avg_cost > 0:
        summary['margin_pct'] = round((credit_price_usd - avg_cost) / credit_price_usd * 100, 1)

    return summary
