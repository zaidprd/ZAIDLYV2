"""Offline tests for the Content Planner (Batch 4). No network (AI mocked)."""
from django.test import TestCase, SimpleTestCase

from accounts.models import User
from projects.models import Project
from ai_service.base import GenerationResult
from strategy import planner
from strategy.planner import score_title, build_content_plan
from strategy.models import DiscoveredKeyword, ContentPlanItem, TopicCluster


class ScoreTitleTests(SimpleTestCase):
    def test_keyword_and_length_boost(self):
        good = score_title("Cara Memilih Panel Listrik Terbaik untuk Industri", "panel listrik")
        bad = score_title("Panel", "panel listrik")
        self.assertGreater(good, bad)


class BuildPlanTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='p', password='x', email='p@p.com')
        self.p = Project.objects.create(user=self.u, name='Panel', language='id',
                                        writing_style='blog')
        self.c = TopicCluster.objects.create(project=self.p, name='Panel')
        for kw, pr in [('panel listrik', 90.0), ('panel lvmdp', 80.0)]:
            DiscoveredKeyword.objects.create(project=self.p, keyword=kw, source='website',
                                             business_value=80, priority_score=pr, cluster=self.c)
        self._orig = planner.generate
        planner.generate = lambda messages, **kw: GenerationResult(
            text="1. Cara Memilih Panel Listrik Terbaik untuk Pabrik\n2. Panel Listrik Murah",
            model='gpt-4o-mini', tokens_in=200, tokens_out=120, duration_ms=1000)

    def tearDown(self):
        planner.generate = self._orig

    def test_creates_plan_items(self):
        items = build_content_plan(self.p, limit=10)
        self.assertEqual(len(items), 2)
        self.assertEqual(ContentPlanItem.objects.filter(project=self.p).count(), 2)

        top = ContentPlanItem.objects.order_by('-priority').first()
        self.assertEqual(top.keyword.keyword, 'panel listrik')
        self.assertEqual(top.status, 'planned')
        self.assertEqual(top.cluster, self.c)
        self.assertIn('Panel Listrik', top.chosen_title)   # best-scored title chosen
        self.assertTrue(top.alt_titles)

    def test_idempotent(self):
        build_content_plan(self.p, limit=10)
        build_content_plan(self.p, limit=10)
        self.assertEqual(ContentPlanItem.objects.filter(project=self.p).count(), 2)

    def test_skips_unanalyzed_keywords(self):
        DiscoveredKeyword.objects.create(project=self.p, keyword='raw kw', source='website')  # business_value null
        build_content_plan(self.p, limit=10)
        self.assertFalse(ContentPlanItem.objects.filter(keyword__keyword='raw kw').exists())
