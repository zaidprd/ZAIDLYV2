"""Tests for the keyword data provider slot (DataForSEO-ready). Metrics stay None."""
from django.test import TestCase, SimpleTestCase

from accounts.models import User
from projects.models import Project
from strategy.models import DiscoveredKeyword
from strategy import keyword_data


class ProviderTests(SimpleTestCase):
    def test_null_provider_returns_none(self):
        data = keyword_data.NullKeywordDataProvider().enrich('panel listrik')
        self.assertEqual(data, {'volume': None, 'difficulty': None, 'cpc': None, 'intent': None})

    def test_factory_default_is_null(self):
        self.assertIsInstance(keyword_data.get_keyword_data_provider(), keyword_data.NullKeywordDataProvider)

    def test_dataforseo_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            keyword_data.get_keyword_data_provider('dataforseo')


class EnrichTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='k', password='x', email='k@k.com')
        self.p = Project.objects.create(user=self.u, name='Panel')
        DiscoveredKeyword.objects.create(project=self.p, keyword='panel listrik', source='website')

    def test_null_enrich_keeps_metrics_none(self):
        keyword_data.enrich_keywords(self.p)
        dk = DiscoveredKeyword.objects.get(project=self.p)
        self.assertIsNone(dk.volume)
        self.assertIsNone(dk.difficulty)
        self.assertIsNone(dk.cpc)

    def test_real_provider_fills_metrics(self):
        class FakeProvider:
            def enrich(self, keyword):
                return {'volume': 1200, 'difficulty': 35.0, 'cpc': 0.4, 'intent': 'commercial'}
        keyword_data.enrich_keywords(self.p, provider=FakeProvider())
        dk = DiscoveredKeyword.objects.get(project=self.p)
        self.assertEqual(dk.volume, 1200)
        self.assertEqual(dk.difficulty, 35.0)
        self.assertEqual(dk.cpc, 0.4)
