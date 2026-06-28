"""Offline test for run_publish_wordpress: schema injection + featured image wiring."""
from django.test import TestCase

from accounts.models import User
from projects.models import Project, WordPressSite
from queue_manager.models import QueueJob
from publisher import tasks as pt


_captured = {}


class FakeClient:
    def __init__(self, site):
        pass

    def upload_image(self, image_url, filename='featured.jpg', alt_text=''):
        _captured['alt_text'] = alt_text
        return 99

    def publish_post(self, **kwargs):
        _captured['publish'] = kwargs
        return {'wp_post_id': 7, 'wp_post_url': 'https://blog.id/artikel', 'wp_status': 'publish'}


class PublishTaskTests(TestCase):
    def setUp(self):
        _captured.clear()
        self.u = User.objects.create_user(username='pub', password='x', email='p@p.com')
        self.p = Project.objects.create(user=self.u, name='P', threads_enabled=False)
        self.site = WordPressSite.objects.create(project=self.p, name='S', url='https://blog.id',
                                                 username='u', app_password='pw')
        self._orig = pt.WordPressClient
        pt.WordPressClient = FakeClient

    def tearDown(self):
        pt.WordPressClient = self._orig

    def test_publish_injects_schema_and_featured_image(self):
        job = QueueJob.objects.create(
            user=self.u, project=self.p, site=self.site,
            job_type=QueueJob.TYPE_PUBLISH, keyword='kopi', title='Kopi Gayo',
            result={
                'article_html': '<h2>Kopi</h2><p>Enak.</p>',
                'meta_title': 'Kopi Gayo Terbaik',
                'meta_description': 'Tentang kopi gayo.',
                'slug': 'kopi-gayo',
                'image_url': 'https://img/x.png',
                'image_alt': 'biji kopi gayo',
                'schema_jsonld': '{"@type":"Article"}',
            },
        )
        pt.run_publish_wordpress(job.id)
        job.refresh_from_db()

        self.assertEqual(job.status, QueueJob.PUBLISHED)
        self.assertEqual(job.result['wp_post_id'], 7)
        self.assertEqual(_captured['alt_text'], 'biji kopi gayo')
        pub = _captured['publish']
        self.assertEqual(pub['featured_media_id'], 99)
        self.assertEqual(pub['meta_title'], 'Kopi Gayo Terbaik')
        self.assertIn('application/ld+json', pub['content'])
        self.assertIn('"@type":"Article"', pub['content'])
