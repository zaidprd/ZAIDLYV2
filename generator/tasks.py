"""Generate task — now a thin orchestrator over the SEO pipeline.

`run_generate_article` wires the provider callables, runs the article pipeline,
persists the accumulated cost/quality telemetry to the job, and triggers
auto-publish. The actual SEO stages live in `pipeline.steps`.

`generate` / `generate_image` are imported here so the task layer owns provider
wiring (and tests can swap them in one place); they are injected into the
PipelineContext rather than imported by the steps.
"""
from decouple import config

from ai_service import generate, generate_image
from ai_service import pricing
from .parsing import slugify, count_words

from pipeline import PipelineContext, build_article_pipeline


def run_generate_article(job_id):
    from queue_manager.models import QueueJob
    from django_q.tasks import async_task
    from billing.credits import deduct, refund

    try:
        job = QueueJob.objects.select_related('project', 'site', 'user').get(pk=job_id)
    except QueueJob.DoesNotExist:
        return

    # Credit check
    user = job.user
    if not deduct(user, job):
        job.mark_failed('Kredit tidak cukup. Tambahkan kredit untuk melanjutkan.')
        return

    job.mark_processing()

    try:
        ctx = PipelineContext(job=job, generate=generate, generate_image=generate_image)
        build_article_pipeline().run(ctx)

        sections = ctx.sections
        seo = ctx.seo
        article_html = sections['ARTICLE_HTML']
        meta_description = sections['META_DESCRIPTION']
        meta_title = sections['META_TITLE'] or job.title
        slug = sections['SLUG'] or slugify(job.title)
        image_alt = sections['IMAGE_ALT'] or job.title
        schema_jsonld = sections['SCHEMA_JSONLD']
        img_url = ctx.image_url

        # Cost / HPP telemetry (accumulated across research, generation + revisions)
        image_model = config('AI_IMAGE_MODEL', default='')
        cost_text = pricing.estimate_text_cost(ctx.model_used, ctx.tokens_in, ctx.tokens_out)
        cost_image = pricing.estimate_image_cost(image_model) if img_url else 0.0
        job.model_used = ctx.model_used
        job.tokens_in = ctx.tokens_in
        job.tokens_out = ctx.tokens_out
        job.cost_text_usd = round(cost_text, 6)
        job.cost_image_usd = round(cost_image, 6)
        job.cost_total_usd = round(cost_text + cost_image, 6)
        job.duration_ms = ctx.duration_ms
        job.word_count = count_words(article_html)
        job.gen_fallback_used = ctx.fallback_used
        job.quality_score = seo['score']
        job.quality_passed = seo['passed']
        job.revision_count = ctx.revision_count
        job.save(update_fields=[
            'model_used', 'tokens_in', 'tokens_out', 'cost_text_usd', 'cost_image_usd',
            'cost_total_usd', 'duration_ms', 'word_count', 'gen_fallback_used',
            'quality_score', 'quality_passed', 'revision_count', 'updated_at',
        ])

        result = {
            'meta_title': meta_title,
            'article_html': article_html,
            'meta_description': meta_description,
            'slug': slug,
            'image_url': img_url,
            'image_alt': image_alt,
            'schema_jsonld': schema_jsonld,
            'seo': seo,
            'quality_passed': seo['passed'],
            'research_snapshot_id': ctx.snapshot.pk if ctx.snapshot else None,
        }
        job.mark_done(result)

        # Auto-publish only when quality gate passed (failing -> needs manual review)
        if job.project.auto_publish and seo['passed']:
            site = job.site or job.project.sites.filter(is_active=True).first()
            if site:
                publish_job = QueueJob.objects.create(
                    user=job.user,
                    project=job.project,
                    site=site,
                    job_type=QueueJob.TYPE_PUBLISH,
                    keyword=job.keyword,
                    title=job.title,
                    result=result,
                    scheduled_at=_next_scheduled_time(job.project),
                )
                eta = publish_job.scheduled_at
                if eta:
                    async_task('publisher.tasks.run_publish_wordpress', publish_job.id, eta=eta)
                else:
                    async_task('publisher.tasks.run_publish_wordpress', publish_job.id)

    except Exception as e:
        job.mark_failed(str(e))
        refund(user, job, f'Refund gagal generate: {job.keyword[:60]}')


def _next_scheduled_time(project):
    from django.utils import timezone
    import datetime

    if not project.schedule_times:
        return None

    now = timezone.localtime()
    times = []
    for t in project.schedule_times.split(','):
        t = t.strip()
        try:
            h, m = map(int, t.split(':'))
            times.append(datetime.time(h, m))
        except ValueError:
            continue

    if not times:
        return None

    today = now.date()
    for t in sorted(times):
        candidate = timezone.make_aware(datetime.datetime.combine(today, t))
        if candidate > now:
            return candidate

    # All times today already passed → schedule for first slot tomorrow
    tomorrow = today + datetime.timedelta(days=1)
    return timezone.make_aware(datetime.datetime.combine(tomorrow, sorted(times)[0]))
