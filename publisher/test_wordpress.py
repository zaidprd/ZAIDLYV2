"""Offline tests for WordPressClient: featured image alt text + Yoast meta. No network."""
from types import SimpleNamespace

from django.test import SimpleTestCase

from publisher import wordpress


class FakeResp:
    def __init__(self, json_data=None):
        self._j = json_data or {}
        self.headers = {'Content-Type': 'image/png'}
        self.content = b'binary'

    def raise_for_status(self):
        pass

    def json(self):
        return self._j


class FakeRequests:
    def __init__(self):
        self.calls = []

    def get(self, url, **kw):
        self.calls.append(('GET', url, kw))
        return FakeResp()

    def post(self, url, **kw):
        self.calls.append(('POST', url, kw))
        if url.endswith('/media'):
            return FakeResp({'id': 123})
        if url.endswith('/media/123'):
            return FakeResp({'id': 123})
        if url.endswith('/posts'):
            return FakeResp({'id': 5, 'link': 'https://blog.id/p', 'status': 'publish'})
        return FakeResp({})


class WordPressClientTests(SimpleTestCase):
    def setUp(self):
        self.fake = FakeRequests()
        self._orig = wordpress.requests
        wordpress.requests = self.fake
        site = SimpleNamespace(url='https://blog.id', username='u', app_password='p')
        self.client = wordpress.WordPressClient(site)

    def tearDown(self):
        wordpress.requests = self._orig

    def test_upload_image_sets_alt_text(self):
        media_id = self.client.upload_image('https://img/x.png', alt_text='masjid pagi')
        self.assertEqual(media_id, 123)
        # the media/123 update call carries alt_text
        update = [c for c in self.fake.calls if c[1].endswith('/media/123')]
        self.assertEqual(len(update), 1)
        self.assertEqual(update[0][2]['json']['alt_text'], 'masjid pagi')

    def test_publish_post_sets_yoast_title_and_desc(self):
        self.client.publish_post(
            title='Judul', content='<p>x</p>', slug='judul',
            meta_description='deskripsi', featured_media_id=123, meta_title='Meta Judul')
        post = [c for c in self.fake.calls if c[1].endswith('/posts')][0]
        meta = post[2]['json']['meta']
        self.assertEqual(meta['_yoast_wpseo_title'], 'Meta Judul')
        self.assertEqual(meta['_yoast_wpseo_metadesc'], 'deskripsi')
        self.assertEqual(post[2]['json']['featured_media'], 123)
