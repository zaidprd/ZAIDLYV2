"""Tests for HPP analytics aggregation (PRD §8)."""
from django.test import TestCase

from accounts.models import User
from projects.models import Project
from queue_manager.models import QueueJob
from billing.analytics import hpp_summary


class HppSummaryTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='hpp', password='x', email='h@h.com')
        self.p = Project.objects.create(user=self.u, name='P')

    def _job(self, cost, tokens_out=2000, quality=80):
        return QueueJob.objects.create(
            user=self.u, project=self.p, job_type=QueueJob.TYPE_GENERATE,
            keyword='k', cost_total_usd=cost, tokens_in=1000, tokens_out=tokens_out,
            quality_score=quality, duration_ms=4000, status=QueueJob.PUBLISHED)

    def test_aggregates(self):
        self._job(0.04)
        self._job(0.06)
        s = hpp_summary(self.u)
        self.assertEqual(s['articles'], 2)
        self.assertAlmostEqual(s['total_cost_usd'], 0.10, places=4)
        self.assertAlmostEqual(s['avg_cost_usd'], 0.05, places=4)
        self.assertEqual(s['avg_quality'], 80.0)
        self.assertIsNone(s['margin_pct'])

    def test_margin_when_price_given(self):
        self._job(0.05)
        s = hpp_summary(self.u, credit_price_usd=0.25)  # avg cost 0.05, price 0.25
        self.assertEqual(s['margin_pct'], 80.0)

    def test_excludes_zero_cost_jobs(self):
        self._job(0.04)
        QueueJob.objects.create(user=self.u, project=self.p, job_type=QueueJob.TYPE_PUBLISH,
                                keyword='k', cost_total_usd=0)
        s = hpp_summary(self.u)
        self.assertEqual(s['articles'], 1)
