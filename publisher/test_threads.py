"""Offline tests for Threads posting. No network."""
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from accounts.models import User
from projects.models import Project, WordPressSite
from queue_manager.models import QueueJob
from publisher import threads as th
from publisher import tasks as pt


class FakeResp:
    def __init__(self, j):
        self._j = j

    def raise_for_status(self):
        pass

    def json(self):
        return self._j


class FakeRequests:
    def __init__(self):
        self.calls = []

    def post(self, url, **kw):
        self.calls.append((url, kw))
        if url.endswith('/threads'):
            return FakeResp({'id': 'CONTAINER1'})
        return FakeResp({'id': 'THREAD9'})


class ThreadsUnitTests(SimpleTestCase):
    def test_build_text(self):
        text = th.build_threads_text('Kopi Gayo', 'https://blog.id/kopi', 'kopi gayo')
        self.assertIn('Kopi Gayo', text)
        self.assertIn('https://blog.id/kopi', text)
        self.assertIn('#kopigayo', text)

    def test_post_to_threads_two_step(self):
        fake = FakeRequests()
        orig = th.requests
        th.requests = fake
        try:
            tid = th.post_to_threads('U1', 'TOKEN', 'hello')
        finally:
            th.requests = orig
        self.assertEqual(tid, 'THREAD9')
        self.assertEqual(len(fake.calls), 2)               # container + publish
        self.assertTrue(fake.calls[0][0].endswith('/threads'))
        self.assertTrue(fake.calls[1][0].endswith('/threads_publish'))


class FakeWPClient:
    def __init__(self, site):
        pass

    def upload_image(self, *a, **k):
        return 1

    def publish_post(self, **kw):
        return {'wp_post_id': 1, 'wp_post_url': 'https://blog.id/p', 'wp_status': 'publish'}


class PublishToThreadsTests(TestCase):
    def setUp(self):
        self.captured = {}
        self.u = User.objects.create_user(username='th', password='x', email='t@t.com')
        self.u.threads_user_id = 'U1'
        self.u.threads_access_token = 'TOKEN'
        self.u.save()
        self.p = Project.objects.create(user=self.u, name='P', threads_enabled=True)
        self.site = WordPressSite.objects.create(project=self.p, name='S', url='https://blog.id',
                                                 username='u', app_password='pw')
        self._owp = pt.WordPressClient
        self._oth = pt.post_to_threads
        pt.WordPressClient = FakeWPClient

        def fake_threads(uid, token, text):
            self.captured['text'] = text
            return 'TH9'
        pt.post_to_threads = fake_threads

    def tearDown(self):
        pt.WordPressClient = self._owp
        pt.post_to_threads = self._oth

    def test_threads_posted_after_publish(self):
        job = QueueJob.objects.create(user=self.u, project=self.p, site=self.site,
                                      job_type=QueueJob.TYPE_PUBLISH, keyword='kopi',
                                      title='Kopi Gayo', result={'article_html': '<p>x</p>', 'slug': 'k'})
        pt.run_publish_wordpress(job.id)
        job.refresh_from_db()
        self.assertEqual(job.result.get('threads_post_id'), 'TH9')
        self.assertIn('Kopi Gayo', self.captured['text'])
