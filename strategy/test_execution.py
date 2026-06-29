"""Offline tests for Execution Queue (Batch 6). Generator mocked, no async run."""
from django.test import TestCase

from accounts.models import User
from projects.models import Project
from queue_manager.models import QueueJob
from strategy import execution
from strategy.campaign import build_manual_campaign
from strategy.models import ContentPlanItem


class TickTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='e', password='x', email='e@e.com')
        self.p = Project.objects.create(user=self.u, name='Toko')
        self.c = build_manual_campaign(self.p, [f'kw {i}' for i in range(5)], articles_per_day=2)
        self._calls = []
        self._orig = execution.async_task
        execution.async_task = lambda path, *a, **k: self._calls.append((path, a))

    def tearDown(self):
        execution.async_task = self._orig

    def test_tick_picks_articles_per_day(self):
        ids = execution.run_campaign_tick(self.c)
        self.assertEqual(len(ids), 2)                              # articles_per_day
        self.assertEqual(len(self._calls), 2)                      # dispatched
        self.assertEqual(ContentPlanItem.objects.filter(campaign=self.c, status='generating').count(), 2)
        self.assertEqual(ContentPlanItem.objects.filter(campaign=self.c, status='planned').count(), 3)


class RunPlanItemTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='r', password='x', email='r@r.com')
        self.p = Project.objects.create(user=self.u, name='Toko')
        self.c = build_manual_campaign(self.p, [{'keyword': 'ban mobil', 'title': 'Ban Mobil Terbaik'}])
        self.item = ContentPlanItem.objects.get(campaign=self.c)
        # pre-seed a cached brief so get_or_create_brief is a cache hit (no AI call)
        from research.models import ContentBrief
        ContentBrief.objects.create(project=self.p, keyword='ban mobil', language='id',
                                    lsi_keywords=['ban radial'], entities=['ban mobil'],
                                    faq=[{'question': 'q', 'answer': 'a'}])

        # mock the existing generator: just mark the created job done
        self._orig = execution.run_generate_article

        def fake_generate(job_id):
            job = QueueJob.objects.get(pk=job_id)
            job.status = QueueJob.PUBLISHED
            job.save(update_fields=['status'])
        execution.run_generate_article = fake_generate

    def tearDown(self):
        execution.run_generate_article = self._orig

    def test_run_plan_item_uses_existing_generator(self):
        execution.run_plan_item(self.item.id)
        self.item.refresh_from_db()
        self.assertIsNotNone(self.item.queue_job)                  # job created + linked
        self.assertEqual(self.item.queue_job.title, 'Ban Mobil Terbaik')
        self.assertIsNotNone(self.item.content_brief)              # cached brief linked
        self.assertEqual(self.item.queue_job.options.get('secondary_keywords'), ['ban radial'])
        self.assertEqual(self.item.status, 'generated')
        self.c.refresh_from_db()
        self.assertEqual(self.c.status, 'completed')               # all items done
        self.assertEqual(self.c.generated_count, 1)

    def test_start_campaign_creates_daily_schedule(self):
        from django_q.models import Schedule
        execution.start_campaign(self.c)
        self.c.refresh_from_db()
        self.assertEqual(self.c.status, 'running')
        sched = Schedule.objects.get(name=f'campaign-{self.c.id}')
        self.assertEqual(sched.func, 'strategy.tasks.tick_campaign')
        self.assertEqual(sched.args, str(self.c.id))
        self.assertEqual(sched.schedule_type, Schedule.DAILY)

    def test_completion_removes_schedule(self):
        from django_q.models import Schedule
        execution.start_campaign(self.c)
        self.assertTrue(Schedule.objects.filter(name=f'campaign-{self.c.id}').exists())
        execution.run_plan_item(self.item.id)            # only item -> campaign completes
        self.assertFalse(Schedule.objects.filter(name=f'campaign-{self.c.id}').exists())
