from django.db import models
from django.conf import settings
from django.utils import timezone


class QueueJob(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    PUBLISHED = 'published'
    FAILED = 'failed'
    PAUSED = 'paused'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Sedang Diproses'),
        (PUBLISHED, 'Published'),
        (FAILED, 'Gagal'),
        (PAUSED, 'Dijeda'),
    ]

    TYPE_GENERATE = 'generate'
    TYPE_PUBLISH = 'publish'

    JOB_TYPE_CHOICES = [
        (TYPE_GENERATE, 'Generate Artikel'),
        (TYPE_PUBLISH, 'Publish ke WordPress'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jobs')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='jobs')
    site = models.ForeignKey('projects.WordPressSite', on_delete=models.SET_NULL, null=True, blank=True)

    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default=TYPE_GENERATE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)

    keyword = models.CharField(max_length=500)
    title = models.CharField(max_length=500, blank=True)
    auto_title = models.BooleanField(default=False)
    options = models.JSONField(default=dict, blank=True)  # per-generation params (length, style, keywords...)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    # Cost/HPP telemetry (PRD §8)
    model_used = models.CharField(max_length=100, blank=True)
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    cost_text_usd = models.FloatField(default=0.0)
    cost_image_usd = models.FloatField(default=0.0)
    cost_total_usd = models.FloatField(default=0.0)
    duration_ms = models.IntegerField(default=0)
    word_count = models.IntegerField(default=0)
    gen_fallback_used = models.BooleanField(default=False)

    # Quality gate (PRD §5)
    quality_score = models.IntegerField(null=True, blank=True)
    quality_passed = models.BooleanField(default=False)
    revision_count = models.IntegerField(default=0)

    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.keyword}"

    @property
    def can_retry(self):
        return self.status == self.FAILED and self.retry_count < self.max_retries

    def mark_processing(self):
        self.status = self.PROCESSING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])

    def mark_done(self, result):
        self.status = self.PUBLISHED
        self.result = result
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'result', 'completed_at', 'updated_at'])

    def mark_failed(self, error):
        self.status = self.FAILED
        self.error_message = error
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
