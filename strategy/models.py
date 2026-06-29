from django.db import models


class BusinessAnalysis(models.Model):
    """Output of the Business Analyzer (Engine Batch 1).

    The AI ANALYSES the business (from the profile + optional homepage text) and
    produces understanding + seed themes that feed keyword discovery. It does NOT
    invent SEO metrics (volume/difficulty/cpc) — those come from real data later.
    """
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE,
                                related_name='analyses')

    summary = models.TextField(blank=True)
    offerings = models.JSONField(default=list, blank=True)        # produk/jasa nyata
    themes = models.JSONField(default=list, blank=True)           # seed topik untuk discovery
    target_audience = models.TextField(blank=True)
    competitor_hints = models.JSONField(default=list, blank=True)
    language = models.CharField(max_length=10, default='id')

    source_url = models.URLField(blank=True)
    website_fetched = models.BooleanField(default=False)

    # telemetry
    provider = models.CharField(max_length=50, blank=True)
    model_used = models.CharField(max_length=100, blank=True)
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    cost_usd = models.FloatField(default=0.0)
    duration_ms = models.IntegerField(default=0)
    raw = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Business analyses'

    def __str__(self):
        return f"Analysis: {self.project.name}"
