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


class TopicCluster(models.Model):
    """A group of related keywords (Keyword Intelligence, Batch 3)."""
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE,
                                related_name='clusters')
    name = models.CharField(max_length=150)
    intent = models.CharField(max_length=30, blank=True)
    priority = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority', 'name']
        unique_together = ('project', 'name')

    def __str__(self):
        return self.name


class DiscoveredKeyword(models.Model):
    """A keyword candidate found from real data (no AI). Metrics stay null until a
    real data provider (DataForSEO/Serper) fills them. Intelligence fields
    (cluster/intent/business_value/priority_score) are set by Batch 3."""
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE,
                                related_name='discovered_keywords')
    keyword = models.CharField(max_length=255)
    source = models.CharField(max_length=30)            # website | sitemap | category
    page_source = models.CharField(max_length=500, blank=True)

    volume = models.IntegerField(null=True, blank=True)
    difficulty = models.FloatField(null=True, blank=True)
    cpc = models.FloatField(null=True, blank=True)
    intent = models.CharField(max_length=30, blank=True)

    # Keyword Intelligence (Batch 3) — AI analysis only
    cluster = models.ForeignKey(TopicCluster, on_delete=models.SET_NULL, null=True,
                                blank=True, related_name='keywords')
    search_intent = models.CharField(max_length=30, blank=True)
    business_value = models.IntegerField(null=True, blank=True)   # 0-100, null if unanalyzed
    priority_score = models.FloatField(default=0.0)

    confidence = models.FloatField(default=0.5)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority_score', 'keyword']
        unique_together = ('project', 'keyword')

    def __str__(self):
        return self.keyword


class ContentPlanItem(models.Model):
    """One row of the reviewable Content Plan: a keyword + chosen title + priority.
    Same item feeds the SHARED article generator (manual or AI campaign)."""
    STATUS = [
        ('planned', 'Planned'),
        ('generating', 'Generating'),
        ('generated', 'Generated'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE,
                                related_name='plan_items')
    keyword = models.ForeignKey(DiscoveredKeyword, on_delete=models.CASCADE,
                                related_name='plan_items')
    cluster = models.ForeignKey(TopicCluster, on_delete=models.SET_NULL, null=True,
                                blank=True, related_name='plan_items')
    chosen_title = models.CharField(max_length=300)
    alt_titles = models.JSONField(default=list, blank=True)
    priority = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS, default='planned')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    queue_job = models.ForeignKey('queue_manager.QueueJob', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='plan_item')
    campaign = models.ForeignKey('Campaign', on_delete=models.SET_NULL, null=True,
                                 blank=True, related_name='items')
    content_brief = models.ForeignKey('research.ContentBrief', on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='plan_items')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority']
        unique_together = ('project', 'keyword')

    def __str__(self):
        return self.chosen_title or self.keyword.keyword


class Campaign(models.Model):
    """A finished SEO strategy. AI mode runs the full pipeline; Manual mode takes
    user-provided keywords/titles. Both feed the SAME article generator."""
    MODE = [('ai', 'AI Campaign'), ('manual', 'Manual Import')]
    STATUS = [
        ('draft', 'Draft'),
        ('building', 'Building'),
        ('plan_ready', 'Plan Ready'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE,
                                related_name='campaigns')
    name = models.CharField(max_length=200, blank=True)
    mode = models.CharField(max_length=10, choices=MODE, default='ai')
    goal = models.CharField(max_length=20, blank=True)
    target_country = models.CharField(max_length=10, default='ID')
    language = models.CharField(max_length=10, default='id')
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    progress_step = models.CharField(max_length=20, default='queued', blank=True)
    articles_per_day = models.PositiveIntegerField(default=3)

    planned_count = models.IntegerField(default=0)
    generated_count = models.IntegerField(default=0)
    published_count = models.IntegerField(default=0)
    total_cost_usd = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name or f"Campaign #{self.pk} ({self.project.name})"

    def recompute_progress(self):
        items = self.items.all()
        self.planned_count = items.count()
        self.generated_count = items.filter(status__in=['generated', 'published']).count()
        self.published_count = items.filter(status='published').count()
        self.save(update_fields=['planned_count', 'generated_count', 'published_count', 'updated_at'])
