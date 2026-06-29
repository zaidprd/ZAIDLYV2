"""Research persistence: every generation must leave a knowledge-base trail.

Research is the company's compounding asset, so running the article pipeline has
to persist a ResearchSnapshot and link it back to the job — even with the stub
provider. No network: ai_service is swapped out.
"""
import os

from django.test import TestCase

from accounts.models import User
from projects.models import Project
from queue_manager.models import QueueJob
from ai_service.base import GenerationResult
from generator import tasks as gt
from research.models import ResearchSnapshot


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


class ResearchSnapshotPersistenceTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='r', password='x', email='r@r.com')
        self.u.credits = 100
        self.u.save()
        self.p = Project.objects.create(user=self.u, name='P', language='id',
                                        tone='educational', writing_style='tutorial',
                                        default_length=1500, auto_publish=False)
        self._orig_gen = gt.generate
        self._orig_img = gt.generate_image
        gt.generate = lambda messages, **kw: GenerationResult(
            text=SAMPLE, model='gpt-4o-mini', tokens_in=1200, tokens_out=2600, duration_ms=4200)
        gt.generate_image = lambda *a, **k: ''
        os.environ.pop('AI_IMAGE_MODEL', None)

    def tearDown(self):
        gt.generate = self._orig_gen
        gt.generate_image = self._orig_img

    def test_snapshot_created_and_linked(self):
        job = QueueJob.objects.create(user=self.u, project=self.p,
                                      job_type=QueueJob.TYPE_GENERATE,
                                      keyword='sholat dhuha', title='Panduan Sholat Dhuha',
                                      options={'length': 1500, 'faq': True})
        gt.run_generate_article(job.id)
        job.refresh_from_db()

        snaps = ResearchSnapshot.objects.filter(keyword='sholat dhuha')
        self.assertEqual(snaps.count(), 1)
        snap = snaps.first()
        self.assertEqual(snap.user, self.u)
        self.assertEqual(snap.project, self.p)
        self.assertEqual(snap.provider, 'stub')
        self.assertEqual(snap.brief.get('keyword'), 'sholat dhuha')   # derived brief stored
        self.assertEqual(job.result['research_snapshot_id'], snap.pk)  # linked back to the job
