import re
from .ai import call_ai, generate_image
from .prompts import titles_prompt, article_prompt, image_prompt
from .seo import validate


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

        # Bulk mode: auto-generate title from keyword
        if job.auto_title or not job.title:
            messages = titles_prompt(
                keyword=job.keyword,
                language=project.language,
                tone=project.get_tone_display(),
                target_audience=project.target_audience,
            )
            raw_titles = call_ai(messages, model=project.ai_model, max_tokens=600, temperature=0.7)
            titles = _parse_titles(raw_titles)
            job.title = titles[0] if titles else job.keyword
            job.save(update_fields=['title', 'updated_at'])

        # Generate article
        messages = article_prompt(
            keyword=job.keyword,
            title=job.title,
            language=project.language,
            tone=project.get_tone_display(),
            target_audience=project.target_audience,
        )
        raw = call_ai(messages, model=project.ai_model, max_tokens=4000)
        meta_description, slug, article_html = _parse_article_output(raw)

        # Generate featured image (skip silently if not configured)
        img_url = ''
        try:
            prompt = image_prompt(job.keyword, job.title)
            img_url = generate_image(prompt)
        except Exception:
            pass

        # SEO validation
        seo = validate(job.keyword, job.title, article_html, meta_description)

        result = {
            'article_html': article_html,
            'meta_description': meta_description,
            'slug': slug or _make_slug(job.title),
            'image_url': img_url,
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


def _parse_article_output(raw):
    lines = raw.strip().split('\n')
    meta_description = ''
    slug = ''
    article_lines = []
    for line in lines:
        if line.startswith('META:'):
            meta_description = line[5:].strip()
        elif line.startswith('SLUG:'):
            slug = line[5:].strip()
        else:
            article_lines.append(line)
    return meta_description, slug, '\n'.join(article_lines).strip()


def _make_slug(title):
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')
    return slug[:80]
