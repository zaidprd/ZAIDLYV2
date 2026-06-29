"""Execution Queue (Engine Batch 6).

Starts a campaign and drips ContentPlanItems into the EXISTING article generator
(run_generate_article) — N per tick. No second generator, no redesign.
"""
from django_q.tasks import async_task

from queue_manager.models import QueueJob
from generator.tasks import run_generate_article
from research.service import get_or_create_brief


def start_campaign(campaign):
    campaign.status = 'running'
    campaign.save(update_fields=['status', 'updated_at'])
    return campaign


def run_campaign_tick(campaign, *, limit=None, dispatch=True):
    """Pick the next planned items (up to articles_per_day) and queue them."""
    limit = limit or campaign.articles_per_day
    items = list(campaign.items.filter(status='planned').order_by('-priority')[:limit])
    for item in items:
        item.status = 'generating'
        item.save(update_fields=['status', 'updated_at'])
        if dispatch:
            async_task('strategy.execution.run_plan_item', item.id)
    return [i.id for i in items]


def run_plan_item(item_id):
    """Generate one article for a ContentPlanItem via the existing generator."""
    from .models import ContentPlanItem

    try:
        item = ContentPlanItem.objects.select_related('project', 'keyword', 'campaign').get(pk=item_id)
    except ContentPlanItem.DoesNotExist:
        return

    project = item.project
    site = project.sites.filter(is_active=True).first()

    # Cached SERP research — reused if already done for this keyword (no wasted tokens).
    options = {}
    brief = None
    try:
        brief = get_or_create_brief(item.keyword.keyword, project=project, language=project.language)
    except Exception:
        brief = None
    if brief:
        if brief.lsi_keywords:
            options['secondary_keywords'] = list(brief.lsi_keywords)[:8]
        if brief.entities:
            options['lsi_keywords'] = list(brief.entities)[:10]
        options['faq'] = bool(brief.faq)

    job = QueueJob.objects.create(
        user=project.user, project=project, site=site,
        job_type=QueueJob.TYPE_GENERATE,
        keyword=item.keyword.keyword, title=item.chosen_title,
        options=options, status=QueueJob.PENDING,
    )
    item.queue_job = job
    item.content_brief = brief
    item.save(update_fields=['queue_job', 'content_brief', 'updated_at'])

    run_generate_article(job.id)          # reuse existing generator + quality gate + publish

    job.refresh_from_db()
    item.status = 'generated' if job.status == QueueJob.PUBLISHED else 'failed'
    item.save(update_fields=['status', 'updated_at'])

    campaign = item.campaign
    if campaign:
        campaign.recompute_progress()
        if not campaign.items.filter(status__in=['planned', 'generating']).exists():
            campaign.status = 'completed'
            campaign.save(update_fields=['status', 'updated_at'])
    return job.id
