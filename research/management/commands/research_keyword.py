"""Run SERP research for a keyword from the CLI (no UI needed).

    python manage.py research_keyword "cara membuat website toko online"
    python manage.py research_keyword "sholat dhuha" --language id --no-save
"""
from django.core.management.base import BaseCommand

from research.service import run_research
from research.base import ResearchError


class Command(BaseCommand):
    help = "Run SERP research for a keyword and (optionally) store the ContentBrief."

    def add_arguments(self, parser):
        parser.add_argument('keyword')
        parser.add_argument('--language', default='id')
        parser.add_argument('--model', default=None)
        parser.add_argument('--no-save', action='store_true')

    def handle(self, *args, **opts):
        try:
            result = run_research(
                opts['keyword'], language=opts['language'],
                model=opts['model'], save=not opts['no_save'],
            )
        except ResearchError as e:
            self.stderr.write(self.style.ERROR(f"Research gagal: {e}"))
            return

        # result is a ContentBrief (saved) or ResearchResult (no-save) — same attrs
        self.stdout.write(self.style.SUCCESS(f"Intent      : {result.search_intent}"))
        self.stdout.write(f"Word count  : {result.recommended_word_count}")
        self.stdout.write(f"Entities    : {len(result.entities)}")
        self.stdout.write(f"PAA         : {len(result.people_also_ask)}")
        self.stdout.write(f"Headings    : {len(result.headings)}")
        self.stdout.write(f"Content gap : {len(result.content_gap)}")
        self.stdout.write(f"Cost USD    : {result.cost_usd}  (model {result.model_used})")
        if not opts['no_save']:
            self.stdout.write(self.style.SUCCESS(f"Saved ContentBrief #{result.pk}"))
