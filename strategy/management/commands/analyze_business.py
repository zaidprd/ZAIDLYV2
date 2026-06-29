"""Run the Business Analyzer for a project from the CLI (no UI).

    python manage.py analyze_business <project_id>
    python manage.py analyze_business <project_id> --no-fetch
"""
from django.core.management.base import BaseCommand, CommandError

from projects.models import Project
from strategy.analyzer import analyze_business


class Command(BaseCommand):
    help = "Analyze a project's business profile into a BusinessAnalysis."

    def add_arguments(self, parser):
        parser.add_argument('project_id', type=int)
        parser.add_argument('--no-fetch', action='store_true', help='Skip homepage fetch.')

    def handle(self, *args, **opts):
        try:
            project = Project.objects.get(pk=opts['project_id'])
        except Project.DoesNotExist:
            raise CommandError(f"Project {opts['project_id']} tidak ditemukan.")

        analysis = analyze_business(project, fetch_website=not opts['no_fetch'])
        self.stdout.write(self.style.SUCCESS(f"Summary   : {analysis.summary}"))
        self.stdout.write(f"Offerings : {len(analysis.offerings)} -> {analysis.offerings}")
        self.stdout.write(f"Themes    : {len(analysis.themes)} -> {analysis.themes}")
        self.stdout.write(f"Audience  : {analysis.target_audience}")
        self.stdout.write(f"Competitor: {analysis.competitor_hints}")
        self.stdout.write(f"Web fetch : {analysis.website_fetched} | cost ${analysis.cost_usd} ({analysis.model_used})")
