"""Tests for the deterministic benchmark scorers — they must separate good from bad."""
from django.test import SimpleTestCase

from generator import benchmark as bm
from generator.prompt_builder import ArticleSpec


GOOD = (
    "<p>Cara menurunkan kolesterol bisa dimulai dari pola makan. Hasilnya terasa dalam beberapa minggu.</p>"
    "<h2>Apa penyebab kolesterol tinggi?</h2><p>Penyebabnya beragam. Selain itu, faktor genetik berperan.</p>"
    "<ul><li>Lemak jenuh</li><li>Kurang gerak</li></ul>"
    "<h2>Bagaimana cara menurunkannya?</h2><p>Perbanyak serat. Misalnya oat dan sayur. Kemudian rutin olahraga.</p>"
    "<h2>Kapan harus ke dokter?</h2><p>Bila angka tetap tinggi. Oleh karena itu pantau berkala.</p>"
    "<h2>FAQ</h2><h3>Apakah olahraga membantu?</h3><p>Ya, sangat membantu.</p>"
    "<h3>Berapa lama hasilnya?</h3><p>Sekitar satu bulan.</p><h3>Amankah tanpa obat?</h3><p>Untuk kasus ringan, ya.</p>"
    "<p>Pelajari panduan lengkapnya dan mulai perbaiki pola makan Anda hari ini.</p>"
)

BAD = (
    "<p>Di era digital ini, kolesterol adalah masalah serius yang dihadapi banyak orang di seluruh dunia "
    "yang ingin hidup sehat dan panjang umur tanpa harus mengonsumsi obat-obatan kimia berbahaya.</p>"
    "<h2>Kolesterol</h2><p>Di era digital ini, kolesterol adalah masalah serius yang dihadapi banyak orang.</p>"
    "<h2>Kolesterol</h2><p>Kolesterol tinggi berbahaya bagi tubuh manusia secara umum dan menyeluruh.</p>"
)


class DeterministicScorerTests(SimpleTestCase):
    def test_good_beats_bad_overall(self):
        spec = ArticleSpec(keyword="cara menurunkan kolesterol", length=400)
        good = bm.score_all("cara menurunkan kolesterol",
                            {"ARTICLE_HTML": GOOD, "META_TITLE": "Cara Menurunkan Kolesterol",
                             "META_DESCRIPTION": "Panduan cara menurunkan kolesterol alami yang mudah diikuti pemula.",
                             "SLUG": "cara-menurunkan-kolesterol", "IMAGE_ALT": "cara menurunkan kolesterol",
                             "SCHEMA_JSONLD": '{"@type":"Article"}'}, spec)
        bad = bm.score_all("cara menurunkan kolesterol",
                           {"ARTICLE_HTML": BAD, "META_TITLE": "Acak", "META_DESCRIPTION": "x",
                            "SLUG": "acak", "IMAGE_ALT": "", "SCHEMA_JSONLD": ""}, spec)
        self.assertGreater(bm.overall_score(good), bm.overall_score(bad))

    def test_cliche_and_repetition_penalised(self):
        self.assertLess(bm.score_human(BAD)["score"], bm.score_human(GOOD)["score"])
        self.assertTrue(any("klise" in n for n in bm.score_human(BAD)["notes"]))
        self.assertLess(bm.score_repetition(BAD)["score"], bm.score_repetition(GOOD)["score"])
        self.assertTrue(bm.score_repetition(BAD)["notes"])

    def test_faq_and_cta_detected_in_good(self):
        self.assertEqual(bm.score_cta(GOOD)["score"], 100)
        self.assertGreaterEqual(bm.score_faq(GOOD)["score"], 60)
        self.assertEqual(bm.score_cta(BAD)["score"], 0)
        self.assertEqual(bm.score_faq(BAD)["score"], 0)

    def test_ai_overview_rewards_structure(self):
        self.assertGreater(bm.score_ai_overview(GOOD)["score"], bm.score_ai_overview(BAD)["score"])

    def test_aggregate_ranks_weakest_first(self):
        results = [
            {"niche": "a", "keyword": "k", "scores": {
                "yoast": {"score": 90, "notes": []}, "readability": {"score": 50, "notes": ["kalimat panjang"]},
                "cta": {"score": 100, "notes": []},
            }, "overall": 80},
        ]
        agg = bm.aggregate(results)
        self.assertEqual(agg["ranked"][0][0], "readability")   # lowest avg first
        self.assertEqual(agg["n"], 1)
