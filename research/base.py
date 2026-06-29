"""Provider-agnostic contract for SERP research.

The app depends only on `ResearchResult` / `ContentBrief`, never on how the data
was obtained — so the source (LLM synthesis now, a real SERP API later) is
swappable purely through configuration (RESEARCH_PROVIDER).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ResearchError(Exception):
    """Raised when a research provider fails."""


@dataclass
class ResearchResult:
    keyword: str
    language: str = 'id'

    search_intent: str = ''
    intent_note: str = ''
    competitors: list = field(default_factory=list)
    headings: list = field(default_factory=list)
    people_also_ask: list = field(default_factory=list)
    related_searches: list = field(default_factory=list)
    entities: list = field(default_factory=list)
    lsi_keywords: list = field(default_factory=list)
    faq: list = field(default_factory=list)
    content_gap: list = field(default_factory=list)
    recommended_word_count: int = 0
    internal_link_opportunities: list = field(default_factory=list)
    external_reference_opportunities: list = field(default_factory=list)
    ai_overview_opportunity: str = ''

    # telemetry
    provider: str = ''
    model_used: str = ''
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    raw: dict = field(default_factory=dict)


class ResearchProvider(ABC):
    name = 'base'

    @abstractmethod
    def research(self, keyword, *, language='id', model=None) -> ResearchResult:
        """Return a structured ResearchResult for a keyword. Raises ResearchError."""
