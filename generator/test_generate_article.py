"""Offline test for run_generate_article: builder -> parse -> telemetry. No network."""
import os

from django.test import TestCase

from accounts.models import User
from projects.models import Project
from queue_manager.models import QueueJob
from ai_service.base import GenerationResult
from generator import tasks as gt
from generator.parsing import parse_article_output


SAMPLE = """<<<META_TITLE>>>
Panduan Sholat Dhuha Sesuai Sunnah
<<<META_DESCRIPTION>>>
Pelajari tata cara sholat dhuha sesuai sunnah, lengkap dengan waktu dan keutamaannya.
<<<SLUG>>>
panduan-sholat-dhuha
<<<IMAGE_PROMPT>>>
A serene mosque interior at morning light, editorial style, no text.
<<<IMAGE_ALT>>>
Suasana masjid saat sholat dhuha
<<<ARTICLE_HTML>>>
<h2>Apa itu sholat dhuha</h2><p>Sholat dhuha adalah ibadah sunnah di pagi hari.</p>
<h2>Tata cara</h2><ul><li>Niat</li><li>Dua rakaat</li></ul>
<<<SCHEMA_JSONLD>>>
{"@context":"https://schema.org","@type":"Article"}
<<<END>>>"""


class ParseTests(TestCase):
    def test_sections_extracted(self):
        s = parse_article_output(SAMPLE)
        self.assertEqual(s['SLUG'], 'panduan-sholat-dhuha')
        self.assertIn('<h2>', s['ARTICLE_HTML'])
        self.assertIn('Article', s['SCHEMA_JSONLD'])

    def test_missing_sections_safe(self):
        s = parse_article_output("<<<SLUG>>>\nx\n<<<END>>>")
        self.assertEqual(s['SLUG'], 'x')
        self.assertEqual(s['ARTICLE_HTML'], '')


class GenerateArticleTaskTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='gen', password='x', email='g@g.com')
        self.u.credits = 1000
        self.u.save()
        self.p = Project.objects.create(user=self.u, name='P', language='id',
                                        tone='educational', writing_style='tutorial',
                                        default_length=1500, auto_publish=False)
        os.environ['AI_IMAGE_MODEL'] = 'dall-e-3'
        self._orig_gen = gt.generate
        self._orig_img = gt.generate_image
        gt.generate = lambda messages, **kw: GenerationResult(
            text=SAMPLE, model='gpt-4o-mini', tokens_in=1200, tokens_out=2600,
            duration_ms=4200, attempts=1, fallback_used=False)
        gt.generate_image = lambda *a, **k: 'https://img.example/x.png'

    def tearDown(self):
        gt.generate = self._orig_gen
        gt.generate_image = self._orig_img
        os.environ.pop('AI_IMAGE_MODEL', None)

    def test_telemetry_and_artefacts(self):
        job = QueueJob.objects.create(user=self.u, project=self.p,
                                      job_type=QueueJob.TYPE_GENERATE,
                                      keyword='sholat dhuha', title='Panduan Sholat Dhuha',
                                      options={'length': 1500, 'faq': True})
        gt.run_generate_article(job.id)
        job.refresh_from_db()

        self.assertEqual(job.status, QueueJob.PUBLISHED)
        self.assertEqual(job.result['slug'], 'panduan-sholat-dhuha')
        self.assertIn('<h2>', job.result['article_html'])
        self.assertEqual(job.result['meta_title'], 'Panduan Sholat Dhuha Sesuai Sunnah')
        self.assertEqual(job.result['image_alt'], 'Suasana masjid saat sholat dhuha')
        # telemetry
        self.assertEqual(job.model_used, 'gpt-4o-mini')
        self.assertEqual(job.tokens_in, 1200)
        self.assertEqual(job.tokens_out, 2600)
        self.assertGreater(job.cost_text_usd, 0)
        self.assertGreater(job.cost_image_usd, 0)
        self.assertAlmostEqual(job.cost_total_usd, job.cost_text_usd + job.cost_image_usd, places=6)
        self.assertGreater(job.word_count, 0)
        self.assertEqual(job.duration_ms, 4200)
        self.assertTrue(job.quality_passed)
        self.assertEqual(job.revision_count, 0)


# A deliberately failing output: keyword absent from meta/body, too short, no FAQ/schema.
BAD = """<<<META_TITLE>>>
Judul Acak
<<<META_DESCRIPTION>>>
Deskripsi singkat tanpa relevansi yang memadai untuk pembaca.
<<<SLUG>>>
judul-acak
<<<IMAGE_PROMPT>>>
random
<<<IMAGE_ALT>>>
gambar
<<<ARTICLE_HTML>>>
<h2>Bagian</h2><p>Teks pendek.</p>
<<<SCHEMA_JSONLD>>>

<<<END>>>"""


class QualityGateRevisionTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='qg', password='x', email='q@q.com')
        self.u.credits = 1000
        self.u.save()
        self.p = Project.objects.create(user=self.u, name='P', language='id',
                                        tone='educational', writing_style='tutorial',
                                        default_length=1500, auto_publish=False)
        self._orig_gen = gt.generate
        self._orig_img = gt.generate_image
        self._calls = {'n': 0}

        def fake_gen(messages, **kw):
            self._calls['n'] += 1
            text = BAD if self._calls['n'] == 1 else SAMPLE  # fail first, fix on revision
            return GenerationResult(text=text, model='gpt-4o-mini', tokens_in=1000,
                                    tokens_out=2000, duration_ms=3000)
        gt.generate = fake_gen
        gt.generate_image = lambda *a, **k: ''

    def tearDown(self):
        gt.generate = self._orig_gen
        gt.generate_image = self._orig_img

    def test_revision_runs_and_accumulates(self):
        job = QueueJob.objects.create(user=self.u, project=self.p,
                                      job_type=QueueJob.TYPE_GENERATE,
                                      keyword='sholat dhuha', title='Panduan Sholat Dhuha',
                                      options={'length': 1500, 'faq': True})
        gt.run_generate_article(job.id)
        job.refresh_from_db()
        self.assertEqual(job.revision_count, 1)            # one auto-revision happened
        self.assertEqual(self._calls['n'], 2)              # initial + 1 revision
        self.assertEqual(job.tokens_in, 2000)              # accumulated 1000 + 1000
        self.assertEqual(job.result['slug'], 'panduan-sholat-dhuha')  # kept the fixed version
