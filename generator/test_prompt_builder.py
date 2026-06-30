"""Tests for the Prompt Builder — the core product asset. Pure, no network/DB."""
from django.test import SimpleTestCase

from projects.models import Project
from generator.prompt_builder import (
    ArticleSpec,
    article_spec_from_project,
    build_article_messages,
    build_titles_messages,
    OUTPUT_SECTIONS,
)


def _system(messages):
    return messages[0]["content"]


class ArticleMessagesTests(SimpleTestCase):
    def _spec(self, **kw):
        base = dict(
            keyword="sholat dhuha", title="Panduan Sholat Dhuha",
            secondary_keywords=["tata cara dhuha"], lsi_keywords=["waktu dhuha"],
            language="id", tone="Edukatif", writing_style="tutorial",
            target_audience="Muslim awam", brand_voice="berbasis dalil",
            length=2000, cta="Pelajari lebih lanjut",
        )
        base.update(kw)
        return ArticleSpec(**base)

    def test_core_directives_present(self):
        sys = _system(build_article_messages(self._spec()))
        self.assertIn("sholat dhuha", sys)
        self.assertIn("2000 kata", sys)
        self.assertIn("Bahasa Indonesia", sys)
        self.assertIn("berbasis dalil", sys)            # brand voice
        self.assertIn("Prasyarat", sys)                  # tutorial skeleton
        self.assertIn("Pelajari lebih lanjut", sys)      # CTA

    def test_output_contract_has_all_sentinels(self):
        sys = _system(build_article_messages(self._spec()))
        for section in OUTPUT_SECTIONS:
            self.assertIn(f"<<<{section}>>>", sys)
        self.assertIn("<<<END>>>", sys)

    def test_link_guardrail_always_present(self):
        sys = _system(build_article_messages(self._spec(internal_links=[], external_links=[])))
        self.assertIn("JANGAN mengarang internal link", sys)

    def test_given_links_are_used_verbatim(self):
        sys = _system(build_article_messages(self._spec(internal_links=["https://x.id/a"])))
        self.assertIn("https://x.id/a", sys)

    def test_toggles_off(self):
        sys = _system(build_article_messages(self._spec(faq=False, schema=False, ai_overview=False)))
        self.assertNotIn("FAQ", sys)
        self.assertIn("kosongkan", sys)                  # schema section disabled
        self.assertNotIn("AI Overview", sys)

    def test_length_5000_label(self):
        sys = _system(build_article_messages(self._spec(length=5000)))
        self.assertIn("5000+ kata", sys)

    def test_premium_quality_directives_present(self):
        sys = _system(build_article_messages(self._spec()))
        self.assertIn("STANDAR KUALITAS", sys)
        self.assertIn("EEAT", sys)
        self.assertIn("SEMANTIC SEO", sys)
        self.assertIn("ANTI-REPETISI", sys)
        self.assertIn("di era digital ini", sys)        # banned-cliché list is present
        self.assertIn("HEADING", sys)

    def test_quality_bar_survives_all_toggles_off(self):
        # Premium quality must NOT depend on FAQ/AI-Overview/schema toggles.
        sys = _system(build_article_messages(self._spec(faq=False, schema=False, ai_overview=False)))
        self.assertIn("STANDAR KUALITAS", sys)
        self.assertIn("EEAT", sys)

    def test_goal_directive(self):
        sys = _system(build_article_messages(self._spec(goal="mendorong pembaca mendaftar")))
        self.assertIn("Tujuan artikel: mendorong pembaca mendaftar", sys)

    def test_ai_overview_block_when_enabled(self):
        sys = _system(build_article_messages(self._spec(ai_overview=True)))
        self.assertIn("GOOGLE AI OVERVIEW", sys)
        self.assertIn("answer-first", sys)

    def test_image_style_steers_prompt(self):
        sys = _system(build_article_messages(self._spec(image_style="flat illustration biru")))
        self.assertIn("flat illustration biru", sys)


class SpecFromProjectTests(SimpleTestCase):
    def test_bridges_project_defaults_and_overrides(self):
        p = Project(language="id", tone="educational", writing_style="listicle",
                    default_length=3000, target_audience="UMKM", brand_voice="ramah",
                    default_cta="Hubungi kami")
        spec = article_spec_from_project(p, keyword="kopi gayo")
        self.assertEqual(spec.writing_style, "listicle")
        self.assertEqual(spec.length, 3000)
        self.assertEqual(spec.brand_voice, "ramah")
        self.assertEqual(spec.cta, "Hubungi kami")
        self.assertEqual(spec.tone, "Edukatif")          # get_tone_display()
        # override wins
        spec2 = article_spec_from_project(p, keyword="kopi gayo", length=1000, writing_style="review")
        self.assertEqual(spec2.length, 1000)
        self.assertEqual(spec2.writing_style, "review")


class TitlesMessagesTests(SimpleTestCase):
    def test_titles_prompt(self):
        sys = _system(build_titles_messages("kopi gayo", count=10, writing_style="listicle"))
        self.assertIn("10 judul", sys)
        self.assertIn("listicle", sys)
