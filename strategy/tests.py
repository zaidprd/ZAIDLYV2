"""Offline tests for the Business Analyzer. No network (fetch disabled, AI mocked)."""
import json

from django.test import TestCase

from accounts.models import User
from projects.models import Project
from ai_service.base import GenerationResult
from strategy import analyzer
from strategy.models import BusinessAnalysis


ANALYSIS_JSON = {
    "summary": "Kontraktor panel listrik Schneider dan Siemens untuk industri.",
    "offerings": ["panel LVMDP", "panel ATS", "panel distribusi"],
    "themes": ["panel listrik industri", "ATS AMF", "perawatan panel"],
    "target_audience": "Pabrik, gedung, dan industri di Indonesia.",
    "competitor_hints": ["kontraktor panel lokal", "distributor Schneider"],
}


class AnalyzeBusinessTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='a', password='x', email='a@a.com')
        self.p = Project.objects.create(
            user=self.u, name='Panel Co', language='id',
            business_description='Kontraktor panel listrik Schneider dan Siemens.',
            niche='panel listrik', target_country='ID', goal='leads',
        )
        self._orig = analyzer.generate
        analyzer.generate = lambda messages, **kw: GenerationResult(
            text=json.dumps(ANALYSIS_JSON), model='gpt-4o-mini',
            tokens_in=600, tokens_out=400, duration_ms=2000)

    def tearDown(self):
        analyzer.generate = self._orig

    def test_persists_analysis(self):
        a = analyzer.analyze_business(self.p, fetch_website=False)
        self.assertIsInstance(a, BusinessAnalysis)
        self.assertIn('panel', a.summary.lower())
        self.assertEqual(len(a.offerings), 3)
        self.assertIn('ATS AMF', a.themes)
        self.assertFalse(a.website_fetched)        # fetch disabled
        self.assertGreater(a.cost_usd, 0)
        self.assertEqual(a.provider, 'llm')

    def test_no_save_returns_object_without_persisting(self):
        a = analyzer.analyze_business(self.p, fetch_website=False, save=False)
        self.assertEqual(a.summary, ANALYSIS_JSON['summary'])
        self.assertEqual(BusinessAnalysis.objects.count(), 0)
