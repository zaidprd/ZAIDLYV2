"""Offline tests for the SERP Research Engine. No network."""
import json

from django.test import TestCase, SimpleTestCase

from accounts.models import User
from projects.models import Project
from ai_service.base import GenerationResult
from research import service
from research.providers import llm
from research.parsing import extract_json, to_int
from research.models import ContentBrief


BRIEF_JSON = {
    "search_intent": "informational",
    "intent_note": "Pengguna ingin belajar tata cara.",
    "competitors": [{"title": "Panduan A", "url": "https://a.id", "angle": "lengkap"}],
    "headings": ["H2: Pengertian", "H2: Tata cara", "H3: Langkah 1"],
    "people_also_ask": ["Apa hukum sholat dhuha?", "Kapan waktu dhuha?"],
    "related_searches": ["niat dhuha", "doa dhuha"],
    "entities": ["sholat dhuha", "rakaat", "waktu dhuha"],
    "lsi_keywords": ["ibadah sunnah", "pagi hari"],
    "faq": [{"question": "Berapa rakaat?", "answer": "Minimal dua rakaat."}],
    "content_gap": ["dalil hadis spesifik", "kesalahan umum"],
    "recommended_word_count": 1600,
    "internal_link_opportunities": ["panduan sholat sunnah"],
    "external_reference_opportunities": ["rumaysho.com"],
    "ai_overview_opportunity": "Jawaban ringkas di awal berpeluang tampil.",
}


class ParsingTests(SimpleTestCase):
    def test_extract_plain_json(self):
        self.assertEqual(extract_json('{"a": 1}'), {"a": 1})

    def test_extract_with_fence_and_prose(self):
        raw = 'Berikut hasilnya:\n```json\n{"a": 2}\n```'
        self.assertEqual(extract_json(raw), {"a": 2})

    def test_extract_bad_returns_empty(self):
        self.assertEqual(extract_json("bukan json"), {})

    def test_to_int(self):
        self.assertEqual(to_int("1600 kata"), 1600)
        self.assertEqual(to_int(None, 0), 0)


class RunResearchTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='r', password='x', email='r@r.com')
        self.p = Project.objects.create(user=self.u, name='P', language='id')
        self._orig = llm.generate
        llm.generate = lambda messages, **kw: GenerationResult(
            text=json.dumps(BRIEF_JSON), model='gpt-4o-mini',
            tokens_in=800, tokens_out=900, duration_ms=3000)

    def tearDown(self):
        llm.generate = self._orig

    def test_run_research_persists_brief(self):
        brief = service.run_research('sholat dhuha', project=self.p, user=self.u)
        self.assertIsInstance(brief, ContentBrief)
        self.assertEqual(brief.search_intent, 'informational')
        self.assertEqual(brief.recommended_word_count, 1600)
        self.assertEqual(len(brief.entities), 3)
        self.assertEqual(len(brief.people_also_ask), 2)
        self.assertEqual(brief.faq[0]['question'], 'Berapa rakaat?')
        self.assertGreater(brief.cost_usd, 0)
        self.assertEqual(brief.provider, 'llm')

    def test_latest_brief_reuse(self):
        service.run_research('sholat dhuha', project=self.p, user=self.u)
        latest = service.latest_brief('sholat dhuha', language='id', project=self.p)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.keyword, 'sholat dhuha')

    def test_no_save_returns_result(self):
        res = service.run_research('sholat dhuha', project=self.p, save=False)
        self.assertEqual(res.search_intent, 'informational')
        self.assertEqual(ContentBrief.objects.count(), 0)

    def test_get_or_create_brief_uses_cache(self):
        first = service.run_research('sholat dhuha', project=self.p, user=self.u)
        # cache hit: research must NOT be called again
        llm.generate = lambda *a, **k: (_ for _ in ()).throw(AssertionError('researched again!'))
        cached = service.get_or_create_brief('sholat dhuha', project=self.p, language='id')
        self.assertEqual(cached.pk, first.pk)
        self.assertEqual(ContentBrief.objects.count(), 1)
