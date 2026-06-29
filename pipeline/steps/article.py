"""ArticleStep — build the spec, assemble the (research-grounded) prompt, generate.

This is where the prompt finally enters the pipeline — deliberately near the end.
The spec is built from project defaults + per-generation overrides, and the prompt
is grounded in ctx.brief (no-op while the brief is a stub).
"""
from ..base import Step
from generator.prompt_builder import article_spec_from_project, build_article_messages
from generator.parsing import parse_article_output


def _max_tokens_for(length):
    """Rough output-token budget for a target word count, capped to a safe ceiling."""
    return min(int(length * 2.2) + 800, 16000)


class ArticleStep(Step):
    name = "article"

    def run(self, ctx):
        job = ctx.job
        project = job.project
        opts = job.options or {}

        spec = article_spec_from_project(
            project,
            keyword=job.keyword,
            title=job.title,
            length=opts.get('length'),
            writing_style=opts.get('writing_style'),
            goal=opts.get('goal'),
            secondary_keywords=opts.get('secondary_keywords'),
            lsi_keywords=opts.get('lsi_keywords'),
            cta=opts.get('cta'),
            image_style=opts.get('image_style'),
            faq=opts.get('faq', True),
            internal_links=opts.get('internal_links'),
            external_links=opts.get('external_links'),
        )
        ctx.spec = spec
        ctx.max_tokens = _max_tokens_for(spec.length)

        gen = ctx.generate(
            build_article_messages(spec, brief=ctx.brief),
            model=project.ai_model,
            max_tokens=ctx.max_tokens,
        )
        ctx.add_usage(gen)
        ctx.output_text = gen.text
        ctx.sections = parse_article_output(gen.text)
