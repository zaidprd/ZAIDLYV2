"""Campaign orchestration (Engine Batch 5).

AI mode runs the full strategy pipeline (Batch 1-4). Manual mode builds a plan
straight from user-provided keywords/titles (no AI discovery). Both produce
ContentPlanItem rows for the SAME article generator (Batch 6 executes them).
"""
from .analyzer import analyze_business
from .discovery.pipeline import DiscoveryPipeline
from .intelligence import analyze_keywords
from .planner import build_content_plan


def build_ai_campaign(project, *, name='', articles_per_day=3, limit=20, model=None):
    from .models import Campaign

    campaign = Campaign.objects.create(
        project=project, name=name, mode='ai', goal=project.goal,
        target_country=project.target_country, language=project.language,
        status='building', articles_per_day=articles_per_day,
    )
    try:
        analyze_business(project)                       # Batch 1
        DiscoveryPipeline().run(project)                # Batch 2
        analyze_keywords(project, model=model)          # Batch 3
        items = build_content_plan(project, limit=limit, model=model)  # Batch 4
        for item in items:
            item.campaign = campaign
            item.save(update_fields=['campaign', 'updated_at'])
        campaign.status = 'plan_ready'
        campaign.save(update_fields=['status', 'updated_at'])
        campaign.recompute_progress()
    except Exception:
        campaign.status = 'failed'
        campaign.save(update_fields=['status', 'updated_at'])
        raise
    return campaign


def build_manual_campaign(project, entries, *, name='', articles_per_day=3):
    """entries: list of dicts {keyword, title?} or plain keyword strings. No AI."""
    from .models import Campaign, DiscoveredKeyword, ContentPlanItem

    campaign = Campaign.objects.create(
        project=project, name=name, mode='manual', goal=project.goal,
        target_country=project.target_country, language=project.language,
        status='plan_ready', articles_per_day=articles_per_day,
    )
    for entry in entries:
        if isinstance(entry, str):
            keyword, title = entry.strip(), ''
        else:
            keyword, title = str(entry.get('keyword', '')).strip(), str(entry.get('title', '')).strip()
        if not keyword:
            continue
        dk, _ = DiscoveredKeyword.objects.get_or_create(
            project=project, keyword=keyword,
            defaults=dict(source='manual', confidence=1.0),
        )
        ContentPlanItem.objects.update_or_create(
            project=project, keyword=dk,
            defaults=dict(chosen_title=title or keyword, priority=dk.priority_score,
                          status='planned', campaign=campaign),
        )
    campaign.recompute_progress()
    return campaign
