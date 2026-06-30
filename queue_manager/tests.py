"""Queue actions: retry must re-enqueue the task, not just flip status."""
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import Project
from queue_manager.models import QueueJob


class QueueRetryTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='q', password='pw12345678', email='q@q.com')
        self.client.force_login(self.u)
        self.p = Project.objects.create(user=self.u, name='P', language='id',
                                        tone='informative', writing_style='blog', default_length=1500)

    def test_retry_re_enqueues_generate_task(self):
        job = QueueJob.objects.create(user=self.u, project=self.p, job_type=QueueJob.TYPE_GENERATE,
                                      keyword='x', title='x', status=QueueJob.FAILED, retry_count=0)
        with mock.patch('django_q.tasks.async_task') as mocked:
            resp = self.client.post(reverse('queue_action', args=[job.pk, 'retry']))
        self.assertEqual(resp.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, QueueJob.PENDING)
        self.assertEqual(job.retry_count, 1)
        mocked.assert_called_once_with('generator.tasks.run_generate_article', job.id)

    def test_retry_re_enqueues_publish_task_for_publish_jobs(self):
        job = QueueJob.objects.create(user=self.u, project=self.p, job_type=QueueJob.TYPE_PUBLISH,
                                      keyword='x', title='x', status=QueueJob.FAILED, retry_count=0)
        with mock.patch('django_q.tasks.async_task') as mocked:
            self.client.post(reverse('queue_action', args=[job.pk, 'retry']))
        mocked.assert_called_once_with('publisher.tasks.run_publish_wordpress', job.id)
