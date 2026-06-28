from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from queue_manager.models import QueueJob


@staff_member_required
def monitoring(request):
    now = timezone.now()
    last_7_days = now - timezone.timedelta(days=7)

    jobs = QueueJob.objects.all()

    stats = {
        'total': jobs.count(),
        'pending': jobs.filter(status=QueueJob.PENDING).count(),
        'processing': jobs.filter(status=QueueJob.PROCESSING).count(),
        'published': jobs.filter(status=QueueJob.PUBLISHED).count(),
        'failed': jobs.filter(status=QueueJob.FAILED).count(),
        'paused': jobs.filter(status=QueueJob.PAUSED).count(),
    }

    recent_failures = jobs.filter(
        status=QueueJob.FAILED,
        updated_at__gte=last_7_days,
    ).select_related('user', 'project').order_by('-updated_at')[:20]

    daily_published = (
        jobs.filter(status=QueueJob.PUBLISHED, completed_at__gte=last_7_days)
        .annotate(day=TruncDate('completed_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    # Django-Q worker status
    try:
        from django_q.monitor import Stat
        workers = Stat.get_all()
    except Exception:
        workers = []

    return render(request, 'monitoring/dashboard.html', {
        'stats': stats,
        'recent_failures': recent_failures,
        'daily_published': list(daily_published),
        'workers': workers,
        'now': now,
    })
