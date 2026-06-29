"""TitleStep — pick a title when running in bulk/auto mode.

Only runs when the job has no explicit title (or auto_title is set). Mirrors the
old bulk behaviour: generate candidate titles from the keyword and take the first.
"""
from ..base import Step
from generator.prompt_builder import build_titles_messages


class TitleStep(Step):
    name = "title"

    def enabled(self, ctx):
        job = ctx.job
        return bool(job.auto_title or not job.title)

    def run(self, ctx):
        job = ctx.job
        project = job.project
        opts = job.options or {}

        messages = build_titles_messages(
            job.keyword,
            language=project.language,
            tone=project.get_tone_display(),
            target_audience=project.target_audience,
            writing_style=opts.get('writing_style') or project.writing_style,
        )
        gen = ctx.generate(messages, model=project.ai_model, max_tokens=600, temperature=0.7)
        ctx.add_usage(gen)
        titles = _parse_titles(gen.text)
        job.title = titles[0] if titles else job.keyword
        job.save(update_fields=['title', 'updated_at'])


def _parse_titles(raw):
    titles = []
    for line in (raw or "").strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        clean = line.lstrip('0123456789.-) ').strip()
        if clean:
            titles.append(clean)
    return titles[:15]
