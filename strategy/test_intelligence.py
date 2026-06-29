"""Offline tests for Keyword Intelligence (Batch 3). No network (AI mocked)."""
import json

from django.test import TestCase, SimpleTestCase

from accounts.models import User
from projects.models import Project
from ai_service.base import GenerationResult
from strategy import intelligence
from strategy.intelligence import compute_priority, analyze_keywords
from strategy.models import DiscoveredKeyword, TopicCluster


AI_JSON = {
    "keywords": [
        {"keyword": "ban mobil murah", "cluster": "Ban Mobil", "intent": "commercial", "business_value": 90},
        {"keyword": "velg racing 17 inch", "cluster": "Velg", "intent": "transactional", "business_value": 80},
        {"keyword": "tips merawat ban", "cluster": "Ban Mobil", "intent": "informational", "business_value": 50},
    ]
}


class PriorityTests(SimpleTestCase):
    def test_null_safe_without_volume(self):
        score = compute_priority(90, 'commercial', 0.7, volume=None, difficulty=None)
        self.assertGreater(score, 0)

    def test_volume_boosts(self):
        base = compute_priority(80, 'commercial', 0.5)
        with_vol = compute_priority(80, 'commercial', 0.5, volume=5000)
        self.assertGreater(with_vol, base)


class AnalyzeKeywordsTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='i', password='x', email='i@i.com')
        self.p = Project.objects.create(user=self.u, name='Toko Ban',
                                        business_description='Jual ban mobil', niche='ban mobil')
        for kw in ['ban mobil murah', 'velg racing 17 inch', 'tips merawat ban']:
            DiscoveredKeyword.objects.create(project=self.p, keyword=kw, source='website')
        self._orig = intelligence.generate
        intelligence.generate = lambda messages, **kw: GenerationResult(
            text=json.dumps(AI_JSON), model='gpt-4o-mini',
            tokens_in=500, tokens_out=400, duration_ms=2000)

    def tearDown(self):
        intelligence.generate = self._orig

    def test_clusters_intent_value_priority_saved(self):
        result = analyze_keywords(self.p)
        self.assertEqual(result['keywords'], 3)
        self.assertEqual(TopicCluster.objects.filter(project=self.p).count(), 2)  # Ban Mobil, Velg

        dk = DiscoveredKeyword.objects.get(project=self.p, keyword='ban mobil murah')
        self.assertEqual(dk.cluster.name, 'Ban Mobil')
        self.assertEqual(dk.search_intent, 'commercial')
        self.assertEqual(dk.business_value, 90)
        self.assertGreater(dk.priority_score, 0)
        # AI must not fabricate these
        self.assertIsNone(dk.volume)
        self.assertIsNone(dk.difficulty)
        self.assertIsNone(dk.cpc)

        # cluster priority rolled up from members
        ban = TopicCluster.objects.get(project=self.p, name='Ban Mobil')
        self.assertGreater(ban.priority, 0)

    def test_no_keywords_safe(self):
        empty = Project.objects.create(user=self.u, name='Empty')
        self.assertEqual(analyze_keywords(empty), {'clusters': 0, 'keywords': 0})
