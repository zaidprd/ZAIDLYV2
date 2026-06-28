import csv
import io

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_q.tasks import async_task

from projects.models import Project, WordPressSite
from queue_manager.models import QueueJob


@login_required
@require_POST
def publish_now(request, job_id):
    job = get_object_or_404(QueueJob, pk=job_id, user=request.user, job_type=QueueJob.TYPE_GENERATE, status=QueueJob.PUBLISHED)

    site_id = request.POST.get('site')
    site = get_object_or_404(WordPressSite, pk=site_id, project=job.project)

    publish_job = QueueJob.objects.create(
        user=request.user,
        project=job.project,
        site=site,
        job_type=QueueJob.TYPE_PUBLISH,
        keyword=job.keyword,
        title=job.title,
        result=job.result,
    )
    async_task('publisher.tasks.run_publish_wordpress', publish_job.id)

    return redirect('generate_result', pk=job.pk)


@login_required
def bulk_new(request):
    projects = Project.objects.filter(user=request.user)
    return render(request, 'publisher/bulk.html', {'projects': projects})


@login_required
@require_POST
def bulk_create(request):
    project_id = request.POST.get('project', '')
    project = get_object_or_404(Project, pk=project_id, user=request.user)

    keywords = []

    # From textarea
    raw_text = request.POST.get('keywords', '').strip()
    if raw_text:
        keywords = [k.strip() for k in raw_text.splitlines() if k.strip()]

    # From CSV upload
    csv_file = request.FILES.get('csv_file')
    if csv_file:
        try:
            content = csv_file.read().decode('utf-8-sig')
            reader = csv.reader(io.StringIO(content))
            for row in reader:
                if row and row[0].strip():
                    keywords.append(row[0].strip())
        except Exception:
            pass

    # Deduplicate, max 200 per batch
    seen = set()
    unique = []
    for kw in keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique.append(kw)
    unique = unique[:200]

    if not unique:
        return render(request, 'publisher/bulk.html', {
            'projects': Project.objects.filter(user=request.user),
            'error': 'Tidak ada keyword yang valid.',
            'selected_project': project,
        })

    site = project.sites.filter(is_active=True).first()
    jobs_created = []

    for kw in unique:
        job = QueueJob.objects.create(
            user=request.user,
            project=project,
            site=site,
            job_type=QueueJob.TYPE_GENERATE,
            keyword=kw,
            auto_title=True,
            status=QueueJob.PENDING,
        )
        async_task('generator.tasks.run_generate_article', job.id)
        jobs_created.append(job)

    return render(request, 'publisher/bulk_success.html', {
        'count': len(jobs_created),
        'project': project,
    })
