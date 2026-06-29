"""Run one drip tick for a campaign (no UI).

    python manage.py run_campaign_tick <campaign_id> [--limit N]
"""
from django.core.management.base import BaseCommand, CommandError

from strategy.models import Campaign
from strategy.execution import run_campaign_tick


class Command(BaseCommand):
    help = "Queue the next N planned items of a campaign into the article generator."

    def add_arguments(self, parser):
        parser.add_argument('campaign_id', type=int)
        parser.add_argument('--limit', type=int, default=None)

    def handle(self, *args, **opts):
        try:
            campaign = Campaign.objects.get(pk=opts['campaign_id'])
        except Campaign.DoesNotExist:
            raise CommandError(f"Campaign {opts['campaign_id']} tidak ditemukan.")
        ids = run_campaign_tick(campaign, limit=opts['limit'])
        self.stdout.write(self.style.SUCCESS(f"Queued {len(ids)} item(s): {ids}"))
