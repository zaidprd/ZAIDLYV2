from decouple import config

from ai_service import generate, generate_image
from ai_service import pricing
from .prompt_builder import (
    build_titles_messages, build_article_messages, build_revision_messages,
    article_spec_from_project,
)
from .parsing import parse_article_output, slugify, count_words
from .seo import score_article


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
        max_tok = _max_tokens_for(spec.length)
        threshold = config('QUALITY_MIN_SCORE', default=70, cast=int)
        max_revisions = config('QUALITY_MAX_REVISIONS', default=1, cast=int)

        def _evaluate(text):
            s = parse_article_output(text)
            seo = score_article(
                keyword=job.keyword,
                meta_title=s['META_TITLE'] or job.title,
                meta_description=s['META_DESCRIPTION'],
                slug=s['SLUG'] or slugify(job.title),
                article_html=s['ARTICLE_HTML'],
                image_alt=s['IMAGE_ALT'] or job.title,
                length_target=spec.length,
                faq_required=spec.faq,
                schema_required=spec.schema,
                schema_jsonld=s['SCHEMA_JSONLD'],
                threshold=threshold,
            )
            return s, seo

        # Initial generation
        gen = generate(build_article_messages(spec), model=project.ai_model, max_tokens=max_tok)
        model_used, tot_in, tot_out, tot_ms = gen.model, gen.tokens_in, gen.tokens_out, gen.duration_ms
        fallback_used = gen.fallback_used
        output_text = gen.text
        sections, seo = _evaluate(output_text)

        # Quality gate: auto-revise failing output until it passes or we run out of tries
        revisions = 0
        while not seo['passed'] and revisions < max_revisions:
            rgen = generate(build_revision_messages(spec, output_text, seo['failures']),
                            model=project.ai_model, max_tokens=max_tok)
            tot_in += rgen.tokens_in
            tot_out += rgen.tokens_out
            tot_ms += rgen.duration_ms
            fallback_used = fallback_used or rgen.fallback_used
            revisions += 1
            new_sections, new_seo = _evaluate(rgen.text)
            if new_seo['score'] >= seo['score']:  # keep the better version
                sections, seo, output_text = new_sections, new_seo, rgen.text
            else:
                break

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

        # Cost / HPP telemetry (accumulated across generation + revisions)
        cost_text = pricing.estimate_text_cost(model_used, tot_in, tot_out)
        cost_image = pricing.estimate_image_cost(image_model) if img_url else 0.0
        job.model_used = model_used
        job.tokens_in = tot_in
        job.tokens_out = tot_out
        job.cost_text_usd = round(cost_text, 6)
        job.cost_image_usd = round(cost_image, 6)
        job.cost_total_usd = round(cost_text + cost_image, 6)
        job.duration_ms = tot_ms
        job.word_count = count_words(article_html)
        job.gen_fallback_used = fallback_used
        job.quality_score = seo['score']
        job.quality_passed = seo['passed']
        job.revision_count = revisions
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
        }
        job.mark_done(result)

        # Auto-publish only when quality gate passed (failing -> needs manual review)
        if project.auto_publish and seo['passed']:
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
