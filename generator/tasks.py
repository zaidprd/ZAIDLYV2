from decouple import config

from ai_service import generate, generate_image
from ai_service import pricing
from .prompt_builder import build_titles_messages, build_article_messages, article_spec_from_project
from .parsing import parse_article_output, slugify, count_words
from .seo import validate


def _max_tokens_for(length):
    """Rough output-token budget for a target word count, capped to a safe ceiling."""
    return min(int(length * 2.2) + 800, 16000)


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
        project = job.project
        opts = job.options or {}

        # Bulk mode: auto-generate title from keyword
        if job.auto_title or not job.title:
            t_messages = build_titles_messages(
                job.keyword,
                language=project.language,
                tone=project.get_tone_display(),
                target_audience=project.target_audience,
                writing_style=opts.get('writing_style') or project.writing_style,
            )
            titles = _parse_titles(generate(t_messages, model=project.ai_model, max_tokens=600, temperature=0.7).text)
            job.title = titles[0] if titles else job.keyword
            job.save(update_fields=['title', 'updated_at'])

        # Build article prompt from project defaults + per-generation overrides
        spec = article_spec_from_project(
            project,
            keyword=job.keyword,
            title=job.title,
            length=opts.get('length'),
            writing_style=opts.get('writing_style'),
            secondary_keywords=opts.get('secondary_keywords'),
            lsi_keywords=opts.get('lsi_keywords'),
            faq=opts.get('faq', True),
            internal_links=opts.get('internal_links'),
            external_links=opts.get('external_links'),
        )
        messages = build_article_messages(spec)
        gen = generate(messages, model=project.ai_model, max_tokens=_max_tokens_for(spec.length))
        sections = parse_article_output(gen.text)

        article_html = sections['ARTICLE_HTML']
        meta_description = sections['META_DESCRIPTION']
        meta_title = sections['META_TITLE'] or job.title
        slug = sections['SLUG'] or slugify(job.title)
        img_prompt = sections['IMAGE_PROMPT']
        image_alt = sections['IMAGE_ALT'] or job.title
        schema_jsonld = sections['SCHEMA_JSONLD']

        # Generate featured image (skip silently if not configured) — Module 8 extends upload+alt
        img_url = ''
        image_model = config('AI_IMAGE_MODEL', default='')
        try:
            img_url = generate_image(img_prompt or job.title)
        except Exception:
            pass

        # SEO validation
        seo = validate(job.keyword, job.title, article_html, meta_description)

        # Cost / HPP telemetry
        cost_text = pricing.estimate_text_cost(gen.model, gen.tokens_in, gen.tokens_out)
        cost_image = pricing.estimate_image_cost(image_model) if img_url else 0.0
        job.model_used = gen.model
        job.tokens_in = gen.tokens_in
        job.tokens_out = gen.tokens_out
        job.cost_text_usd = round(cost_text, 6)
        job.cost_image_usd = round(cost_image, 6)
        job.cost_total_usd = round(cost_text + cost_image, 6)
        job.duration_ms = gen.duration_ms
        job.word_count = count_words(article_html)
        job.gen_fallback_used = gen.fallback_used
        job.save(update_fields=[
            'model_used', 'tokens_in', 'tokens_out', 'cost_text_usd', 'cost_image_usd',
            'cost_total_usd', 'duration_ms', 'word_count', 'gen_fallback_used', 'updated_at',
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
        }
        job.mark_done(result)

        # Auto-publish: queue publish job if project has auto_publish + active site
        if project.auto_publish:
            site = job.site or project.sites.filter(is_active=True).first()
            if site:
                publish_job = QueueJob.objects.create(
                    user=job.user,
                    project=project,
                    site=site,
                    job_type=QueueJob.TYPE_PUBLISH,
                    keyword=job.keyword,
                    title=job.title,
                    result=result,
                    scheduled_at=_next_scheduled_time(project),
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


def _parse_titles(raw):
    titles = []
    for line in raw.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        clean = line.lstrip('0123456789.-) ').strip()
        if clean:
            titles.append(clean)
    return titles[:15]
