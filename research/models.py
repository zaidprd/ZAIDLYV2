from django.conf import settings
from django.db import models


class ContentBrief(models.Model):
    """SERP research result for a keyword, persisted as reusable knowledge base.

    Drives prompt building (Batch 2) and scoring (Batch 3) — the article is
    written against this brief, not the raw keyword.
    """
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE,
                                related_name='briefs', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='briefs', null=True, blank=True)
    keyword = models.CharField(max_length=300, db_index=True)
    language = models.CharField(max_length=10, default='id')

    # Research outputs
    search_intent = models.CharField(max_length=50, blank=True)
    intent_note = models.TextField(blank=True)
    competitors = models.JSONField(default=list, blank=True)
    headings = models.JSONField(default=list, blank=True)
    people_also_ask = models.JSONField(default=list, blank=True)
    related_searches = models.JSONField(default=list, blank=True)
    entities = models.JSONField(default=list, blank=True)
    lsi_keywords = models.JSONField(default=list, blank=True)
    faq = models.JSONField(default=list, blank=True)
    content_gap = models.JSONField(default=list, blank=True)
    recommended_word_count = models.PositiveIntegerField(default=0)
    internal_link_opportunities = models.JSONField(default=list, blank=True)
    external_reference_opportunities = models.JSONField(default=list, blank=True)
    ai_overview_opportunity = models.TextField(blank=True)

    # Telemetry / provenance
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
        indexes = [models.Index(fields=['keyword', 'language'])]

    def __str__(self):
        return f"Brief: {self.keyword} ({self.search_intent or 'intent?'})"
