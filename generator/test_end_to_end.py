"""End-to-end generate flow with the mock provider — proves the product runs offline.

Uses the real ai_service wiring (MockProvider, no monkeypatched lambda, no API key)
so the whole job path is exercised: credit deduction, pipeline, telemetry, research
snapshot, and result artefacts.
"""
from django.test import TestCase

import ai_service
from ai_service.providers.mock import MockProvider
from accounts.models import User
from projects.models import Project
from queue_manager.models import QueueJob
from research.models import ResearchSnapshot
from generator import tasks as gt


class MockProviderEndToEndTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='e2e', password='x', email='e2e@e.com')
        self.u.credits = 10
        self.u.save()
        self.p = Project.objects.create(user=self.u, name='P', language='id', tone='informative',
                                        writing_style='blog', default_length=1500, auto_publish=False)
        self._orig = ai_service._provider
        ai_service._provider = MockProvider()  # real provider object, no network

    def tearDown(self):
        ai_service._provider = self._orig

    def test_full_generate_flow_offline(self):
        job = QueueJob.objects.create(user=self.u, project=self.p, job_type=QueueJob.TYPE_GENERATE,
                                      keyword='cara memulai bisnis online', title='Panduan Bisnis Online',
                                      options={'length': 1500, 'faq': True})
        gt.run_generate_article(job.id)
        job.refresh_from_db()
        self.u.refresh_from_db()

        self.assertEqual(job.status, QueueJob.PUBLISHED)
        self.assertIn('<h2', job.result['article_html'])
        self.assertGreater(job.word_count, 50)
        self.assertTrue(job.model_used)                           # telemetry recorded
        self.assertGreater(job.cost_total_usd, 0)
        self.assertTrue(job.quality_passed)
        self.assertEqual(self.u.credits, 9)                       # one credit deducted
        self.assertTrue(ResearchSnapshot.objects.filter(keyword='cara memulai bisnis online').exists())
