"""Offline tests for Campaign orchestration (Batch 5). Pipeline stubbed."""
from django.test import TestCase

from accounts.models import User
from projects.models import Project
from strategy import campaign as camp
from strategy.models import Campaign, DiscoveredKeyword, ContentPlanItem


class ManualCampaignTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='m', password='x', email='m@m.com')
        self.p = Project.objects.create(user=self.u, name='Toko', goal='leads')

    def test_manual_builds_plan_without_ai(self):
        c = camp.build_manual_campaign(self.p, [
            {'keyword': 'ban mobil murah', 'title': 'Ban Mobil Murah Terbaik'},
            'velg racing',
        ])
        self.assertEqual(c.mode, 'manual')
        self.assertEqual(c.status, 'plan_ready')
        self.assertEqual(ContentPlanItem.objects.filter(campaign=c).count(), 2)
        self.assertEqual(c.planned_count, 2)
        # keyword stored from manual source, metrics null
        dk = DiscoveredKeyword.objects.get(keyword='velg racing')
        self.assertEqual(dk.source, 'manual')
        self.assertIsNone(dk.volume)


class AiCampaignTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='a', password='x', email='a@a.com')
        self.p = Project.objects.create(user=self.u, name='Panel', goal='traffic')

        # stub the whole pipeline — this is an orchestration test
        self._orig = (camp.analyze_business, camp.DiscoveryPipeline,
                      camp.analyze_keywords, camp.build_content_plan)

        camp.analyze_business = lambda project, **k: None

        class FakePipeline:
            def run(self, project, save=True):
                DiscoveredKeyword.objects.create(project=project, keyword='panel listrik',
                                                 source='website', business_value=90, priority_score=88.0)
                return []
        camp.DiscoveryPipeline = FakePipeline
        camp.analyze_keywords = lambda project, **k: {'clusters': 1, 'keywords': 1}

        def fake_plan(project, **k):
            dk = DiscoveredKeyword.objects.get(project=project, keyword='panel listrik')
            item = ContentPlanItem.objects.create(project=project, keyword=dk,
                                                  chosen_title='Cara Memilih Panel Listrik',
                                                  priority=dk.priority_score, status='planned')
            return [item]
        camp.build_content_plan = fake_plan

    def tearDown(self):
        (camp.analyze_business, camp.DiscoveryPipeline,
         camp.analyze_keywords, camp.build_content_plan) = self._orig

    def test_ai_campaign_orchestrates_and_links(self):
        c = camp.build_ai_campaign(self.p, name='Q3', articles_per_day=5)
        self.assertEqual(c.mode, 'ai')
        self.assertEqual(c.status, 'plan_ready')
        self.assertEqual(c.articles_per_day, 5)
        self.assertEqual(c.planned_count, 1)
        item = ContentPlanItem.objects.get(project=self.p)
        self.assertEqual(item.campaign, c)        # plan linked to campaign
