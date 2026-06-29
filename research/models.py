"""SEO knowledge base — research is the company's compounding asset.

Every keyword we research is persisted as a ResearchSnapshot (the SERP-level
findings) plus one CompetitorPage per ranking competitor. The article pipeline
derives a ContentBrief from this data, but the RAW data is kept forever so it can
later power content refresh, content audit, competitor compare, topical maps,
keyword clusters, rank analysis, and AI Overview analysis.

Design note: this is intentionally SEO-specific, not a generic store. Fields map
directly to the SEO signals we care about — no premature abstraction.
"""
from django.db import models
from django.conf import settings


class ResearchSnapshot(models.Model):
    """One capture of the Google SERP for a keyword, with aggregated signals."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='research')
    project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='research')

    keyword = models.CharField(max_length=500)
    language = models.CharField(max_length=10, default='id')
    gl = models.CharField(max_length=10, default='id', help_text='Google country (geo) code.')
    provider = models.CharField(max_length=50, default='stub', help_text="SERP source, e.g. 'serper' or 'stub'.")

    # Aggregated SERP signals
    search_intent = models.CharField(max_length=50, blank=True)  # informational/commercial/transactional/navigational
    ai_overview_present = models.BooleanField(null=True, blank=True)
    median_word_count = models.IntegerField(default=0)
    paa = models.JSONField(default=list, blank=True)                 # People Also Ask questions
    related_searches = models.JSONField(default=list, blank=True)
    entities = models.JSONField(default=list, blank=True)
    semantic_keywords = models.JSONField(default=list, blank=True)   # LSI / semantic
    subtopics = models.JSONField(default=list, blank=True)           # union of competitor themes (coverage target)

    raw = models.JSONField(default=dict, blank=True)    # untouched provider payload (audit/replay)
    brief = models.JSONField(default=dict, blank=True)  # derived ContentBrief snapshot at generation time

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['keyword', 'gl'])]

    def __str__(self):
        return f"SERP[{self.gl}] {self.keyword} ({self.provider})"


class CompetitorPage(models.Model):
    """A single ranking competitor page within a snapshot — the raw scraped signals."""

    snapshot = models.ForeignKey(ResearchSnapshot, on_delete=models.CASCADE, related_name='competitors')

    position = models.IntegerField(default=0)
    url = models.URLField(max_length=1000)
    title = models.CharField(max_length=500, blank=True)
    meta_description = models.TextField(blank=True)
    h1 = models.CharField(max_length=500, blank=True)
    h2 = models.JSONField(default=list, blank=True)
    h3 = models.JSONField(default=list, blank=True)
    faq = models.JSONField(default=list, blank=True)
    word_count = models.IntegerField(default=0)
    schema_types = models.JSONField(default=list, blank=True)          # schema.org types used
    image_alts = models.JSONField(default=list, blank=True)            # alt-text patterns
    internal_link_opps = models.JSONField(default=list, blank=True)    # same-domain links worth mirroring
    external_authority_opps = models.JSONField(default=list, blank=True)  # authoritative outbound links
    publish_date = models.CharField(max_length=100, blank=True)        # kept as raw string (formats vary)
    last_update = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"#{self.position} {self.url}"
