"""ContentBrief — the processed output of research that the prompt consumes.

The pipeline turns a ResearchSnapshot (raw SERP data) into this compact brief.
ONLY the brief reaches the prompt; the raw research stays in the database as the
company knowledge base. Keep this a plain dataclass — it is data flowing through
the pipeline, not a model.
"""
from dataclasses import dataclass, field, asdict


@dataclass
class ContentBrief:
    keyword: str
    intent: str = "informational"
    language: str = "id"
    competitor_titles: list = field(default_factory=list)
    headings: list = field(default_factory=list)          # notable H2/H3 across competitors
    paa: list = field(default_factory=list)
    related_searches: list = field(default_factory=list)
    entities: list = field(default_factory=list)
    semantic_keywords: list = field(default_factory=list)
    subtopics_required: list = field(default_factory=list)  # coverage target for the quality gate
    median_word_count: int = 0
    snapshot_id: int | None = None

    def to_dict(self):
        return asdict(self)

    @property
    def is_grounded(self):
        """True when the brief carries real SERP signal (not an empty stub)."""
        return bool(self.subtopics_required or self.entities or self.paa or self.headings)

    @classmethod
    def from_snapshot(cls, snapshot):
        """Build a brief from a persisted ResearchSnapshot."""
        titles = [c.title for c in snapshot.competitors.all() if c.title]
        return cls(
            keyword=snapshot.keyword,
            intent=snapshot.search_intent or "informational",
            language=snapshot.language,
            competitor_titles=titles,
            paa=list(snapshot.paa or []),
            related_searches=list(snapshot.related_searches or []),
            entities=list(snapshot.entities or []),
            semantic_keywords=list(snapshot.semantic_keywords or []),
            subtopics_required=list(snapshot.subtopics or []),
            median_word_count=snapshot.median_word_count or 0,
            snapshot_id=snapshot.pk,
        )
