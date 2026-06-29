"""django_q task entrypoints for the Strategy Engine (single queue, no new system)."""


def run_build_ai_campaign(campaign_id, model=None, limit=20, refresh=False):
    """Heavy campaign build, run on the django_q worker."""
    from .models import Campaign
    from .campaign import build_ai_campaign

    try:
        campaign = Campaign.objects.select_related('project').get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return
    build_ai_campaign(campaign.project, campaign=campaign, model=model, limit=limit, refresh=refresh)
    return campaign_id


def tick_campaign(campaign_id):
    """Scheduled daily drip: process the next batch of plan items for a campaign."""
    from .models import Campaign
    from .execution import run_campaign_tick

    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return
    return run_campaign_tick(campaign)
