from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from .models import QueueJob


@login_required
def queue_list(request):
    jobs = QueueJob.objects.filter(user=request.user).select_related('project', 'site')
    status_filter = request.GET.get('status', '')
    project_filter = request.GET.get('project', '')
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    if project_filter:
        jobs = jobs.filter(project_id=project_filter)

    from projects.models import Project
    projects = Project.objects.filter(user=request.user)
    return render(request, 'queue_manager/list.html', {
        'jobs': jobs,
        'projects': projects,
        'status_filter': status_filter,
        'project_filter': project_filter,
    })


@login_required
def queue_detail(request, pk):
    job = get_object_or_404(QueueJob, pk=pk, user=request.user)
    return render(request, 'queue_manager/detail.html', {'job': job})


@login_required
def queue_action(request, pk, action):
    if request.method != 'POST':
        return HttpResponse(status=405)

    job = get_object_or_404(QueueJob, pk=pk, user=request.user)

    if action == 'retry' and job.can_retry:
        job.status = QueueJob.PENDING
        job.retry_count += 1
        job.error_message = ''
        job.started_at = None
        job.completed_at = None
        job.save()
    elif action == 'pause' and job.status == QueueJob.PENDING:
        job.status = QueueJob.PAUSED
        job.save(update_fields=['status', 'updated_at'])
    elif action == 'resume' and job.status == QueueJob.PAUSED:
        job.status = QueueJob.PENDING
        job.save(update_fields=['status', 'updated_at'])
    elif action == 'cancel' and job.status in (QueueJob.PENDING, QueueJob.PAUSED):
        job.status = QueueJob.FAILED
        job.error_message = 'Dibatalkan oleh pengguna.'
        job.completed_at = timezone.now()
        job.save()

    return render(request, 'components/job_row.html', {'job': job})


@login_required
def queue_status_poll(request, pk):
    job = get_object_or_404(QueueJob, pk=pk, user=request.user)
    return render(request, 'components/job_row.html', {'job': job})


@login_required
def dashboard_summary(request):
    jobs = QueueJob.objects.filter(user=request.user)
    context = {
        'user': request.user,
        'total_jobs': jobs.count(),
        'pending': jobs.filter(status=QueueJob.PENDING).count(),
        'processing': jobs.filter(status=QueueJob.PROCESSING).count(),
        'published': jobs.filter(status=QueueJob.PUBLISHED).count(),
        'failed': jobs.filter(status=QueueJob.FAILED).count(),
        'projects_count': request.user.projects.count(),
        'recent_jobs': jobs[:5],
    }
    return render(request, 'dashboard.html', context)
