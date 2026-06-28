from django.contrib import admin
from .models import QueueJob


@admin.register(QueueJob)
class QueueJobAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'user', 'project', 'job_type', 'status', 'retry_count', 'created_at')
    list_filter = ('status', 'job_type')
    search_fields = ('keyword', 'title', 'user__email')
    readonly_fields = ('started_at', 'completed_at', 'created_at', 'updated_at', 'result', 'error_message')
    actions = ['reset_to_pending']

    @admin.action(description='Reset ke Pending')
    def reset_to_pending(self, request, queryset):
        queryset.filter(status=QueueJob.FAILED).update(status=QueueJob.PENDING, error_message='')
