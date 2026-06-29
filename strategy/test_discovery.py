"""Offline tests for the Discovery Pipeline. No network (http.fetch mocked)."""
from django.test import TestCase, SimpleTestCase

from accounts.models import User
from projects.models import Project
from strategy.discovery import http, collectors
from strategy.discovery.collectors import WebsiteCollector, SitemapCollector, CategoryCollector, BlogCollector
from strategy.discovery.pipeline import DiscoveryPipeline
from strategy.models import DiscoveredKeyword


HOME_HTML = """
<html><head>
<title>Jual Ban Mobil Murah</title>
<meta name="keywords" content="ban mobil, velg racing, ban bekas">
</head><body>
<h1>Toko Ban Mobil</h1>
<h2>Ban Mobil SUV</h2>
<a href="/product-category/ban-suv">Ban SUV</a>
<a href="/kategori/velg-racing">Velg Racing</a>
<a href="/about">About</a>
</body></html>
"""

SITEMAP_XML = """<?xml version="1.0"?>
<urlset>
  <url><loc>https://toko.id/ban-mobil-murah</loc></url>
  <url><loc>https://toko.id/velg-racing-17-inch</loc></url>
  <url><loc>https://toko.id/image.jpg</loc></url>
</urlset>
"""


def _fake_fetch(url, timeout=10):
    if url.endswith('/sitemap.xml'):
        return SITEMAP_XML
    return HOME_HTML


class CollectorTests(SimpleTestCase):
    def setUp(self):
        self._orig = http.fetch
        collectors.http.fetch = _fake_fetch

    def tearDown(self):
        collectors.http.fetch = self._orig

    def _project(self):
        return Project(name='Toko', website_url='https://toko.id')

    def test_website_collector(self):
        cands = WebsiteCollector().collect(self._project())
        kws = {c.keyword.lower() for c in cands}
        self.assertIn('jual ban mobil murah', kws)   # title
        self.assertIn('ban mobil suv', kws)           # heading
        self.assertIn('velg racing', kws)             # meta keywords
        self.assertTrue(all(c.source == 'website' for c in cands))

    def test_sitemap_collector_skips_files(self):
        cands = SitemapCollector().collect(self._project())
        kws = {c.keyword for c in cands}
        self.assertIn('ban mobil murah', kws)
        self.assertIn('velg racing 17 inch', kws)
        self.assertNotIn('image', kws)                # .jpg skipped

    def test_category_collector(self):
        cands = CategoryCollector().collect(self._project())
        kws = {c.keyword for c in cands}
        self.assertIn('ban suv', kws)
        self.assertIn('velg racing', kws)
        self.assertNotIn('about', kws)                # not a category link

    def test_empty_collector(self):
        self.assertEqual(BlogCollector().collect(self._project()), [])

    def test_no_url_returns_empty(self):
        self.assertEqual(WebsiteCollector().collect(Project(name='x', website_url='')), [])


class PipelineTests(TestCase):
    def setUp(self):
        self._orig = http.fetch
        collectors.http.fetch = _fake_fetch
        self.u = User.objects.create_user(username='d', password='x', email='d@d.com')
        self.p = Project.objects.create(user=self.u, name='Toko', website_url='https://toko.id')

    def tearDown(self):
        collectors.http.fetch = self._orig

    def test_run_saves_and_dedupes(self):
        saved = DiscoveryPipeline().run(self.p)
        self.assertGreater(len(saved), 0)
        # all persisted, unique per (project, keyword)
        self.assertEqual(DiscoveredKeyword.objects.filter(project=self.p).count(), len(saved))
        kws = list(DiscoveredKeyword.objects.values_list('keyword', flat=True))
        self.assertEqual(len(kws), len(set(k.lower() for k in kws)))
        # metrics stay null (no AI, no data provider)
        first = DiscoveredKeyword.objects.first()
        self.assertIsNone(first.volume)
        self.assertIsNone(first.difficulty)

    def test_run_is_idempotent(self):
        DiscoveryPipeline().run(self.p)
        n1 = DiscoveredKeyword.objects.count()
        DiscoveryPipeline().run(self.p)
        self.assertEqual(DiscoveredKeyword.objects.count(), n1)
