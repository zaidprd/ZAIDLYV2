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
        self._orig = (camp.analyze_business, camp.discover_keywords,
                      camp.analyze_keywords, camp.build_content_plan)

        camp.analyze_business = lambda project, **k: None

        def fake_discover(project, **k):
            DiscoveredKeyword.objects.create(project=project, keyword='panel listrik',
                                             source='website', business_value=90, priority_score=88.0)
            return []
        camp.discover_keywords = fake_discover
        camp.analyze_keywords = lambda project, **k: {'clusters': 1, 'keywords': 1}

        def fake_plan(project, **k):
            dk = DiscoveredKeyword.objects.get(project=project, keyword='panel listrik')
            item = ContentPlanItem.objects.create(project=project, keyword=dk,
                                                  chosen_title='Cara Memilih Panel Listrik',
                                                  priority=dk.priority_score, status='planned')
            return [item]
        camp.build_content_plan = fake_plan

    def tearDown(self):
        (camp.analyze_business, camp.discover_keywords,
         camp.analyze_keywords, camp.build_content_plan) = self._orig

    def test_ai_campaign_orchestrates_and_links(self):
        c = camp.build_ai_campaign(self.p, name='Q3', articles_per_day=5)
        self.assertEqual(c.mode, 'ai')
        self.assertEqual(c.status, 'plan_ready')
        self.assertEqual(c.progress_step, 'completed')
        self.assertEqual(c.articles_per_day, 5)
        self.assertEqual(c.planned_count, 1)
        item = ContentPlanItem.objects.get(project=self.p)
        self.assertEqual(item.campaign, c)        # plan linked to campaign


class StartAiCampaignTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='s', password='x', email='s@s.com')
        self.p = Project.objects.create(user=self.u, name='Panel', goal='traffic')
        self.calls = []
        self._orig = camp.async_task
        camp.async_task = lambda path, *a, **k: self.calls.append((path, a))

    def tearDown(self):
        camp.async_task = self._orig

    def test_start_returns_instantly_and_queues(self):
        c = camp.start_ai_campaign(self.p)
        self.assertEqual(c.status, 'building')
        self.assertEqual(c.progress_step, 'queued')
        self.assertEqual(len(self.calls), 1)                      # queued, not run inline
        self.assertEqual(self.calls[0][0], 'strategy.tasks.run_build_ai_campaign')
        self.assertEqual(self.calls[0][1][0], c.id)
