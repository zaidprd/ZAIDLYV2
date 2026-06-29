"""ValidateStep — the quality gate with auto-revision (PRD §5).

Scores the generated article and, if it fails the threshold, asks the model to
fix exactly what failed (up to QUALITY_MAX_REVISIONS), keeping the better version.
Today the scorer is the keyword/Yoast checklist; it evolves into a coverage scorer
(brief subtopics/entities/PAA) as research grounding comes online.
"""
from decouple import config

from ..base import Step
from generator.prompt_builder import build_revision_messages
from generator.parsing import parse_article_output, slugify
from generator.seo import score_article


class ValidateStep(Step):
    name = "validate"

    def run(self, ctx):
        job = ctx.job
        project = job.project
        spec = ctx.spec
        threshold = config('QUALITY_MIN_SCORE', default=70, cast=int)
        max_revisions = config('QUALITY_MAX_REVISIONS', default=1, cast=int)

        def score(sections):
            return score_article(
                keyword=job.keyword,
                meta_title=sections['META_TITLE'] or job.title,
                meta_description=sections['META_DESCRIPTION'],
                slug=sections['SLUG'] or slugify(job.title),
                article_html=sections['ARTICLE_HTML'],
                image_alt=sections['IMAGE_ALT'] or job.title,
                length_target=spec.length,
                faq_required=spec.faq,
                schema_required=spec.schema,
                schema_jsonld=sections['SCHEMA_JSONLD'],
                threshold=threshold,
            )

        seo = score(ctx.sections)
        revisions = 0
        while not seo['passed'] and revisions < max_revisions:
            rgen = ctx.generate(
                build_revision_messages(spec, ctx.output_text, seo['failures']),
                model=project.ai_model,
                max_tokens=ctx.max_tokens,
                temperature=config('AI_ARTICLE_TEMPERATURE', default=0.6, cast=float),
            )
            ctx.add_usage(rgen)
            revisions += 1
            new_sections = parse_article_output(rgen.text)
            new_seo = score(new_sections)
            if new_seo['score'] >= seo['score']:  # keep the better version
                ctx.sections, seo, ctx.output_text = new_sections, new_seo, rgen.text
            else:
                break

        ctx.seo = seo
        ctx.revision_count = revisions
