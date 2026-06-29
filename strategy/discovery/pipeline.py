"""DiscoveryPipeline — run all collectors, dedupe, persist DiscoveredKeyword."""
from .collectors import (
    WebsiteCollector, SitemapCollector, CategoryCollector,
    BlogCollector, CompetitorCollector, SERPCollector, PAACollector, RelatedCollector,
)

DEFAULT_COLLECTORS = [
    WebsiteCollector, SitemapCollector, CategoryCollector,
    BlogCollector, CompetitorCollector, SERPCollector, PAACollector, RelatedCollector,
]


def discover_keywords(project, *, refresh=False):
    """Cached discovery: reuse stored keywords unless `refresh` is requested."""
    from strategy.models import DiscoveredKeyword
    existing = DiscoveredKeyword.objects.filter(project=project)
    if not refresh and existing.exists():
        return list(existing)               # cache hit — no re-discovery, no requests
    return DiscoveryPipeline().run(project)


class DiscoveryPipeline:
    def __init__(self, collectors=None):
        self.collectors = [c() for c in (collectors or DEFAULT_COLLECTORS)]

    def run(self, project, save=True):
        candidates = []
        for collector in self.collectors:
            try:
                candidates.extend(collector.collect(project) or [])
            except Exception:
                continue

        # dedupe by normalized keyword
        seen = set()
        unique = []
        for cand in candidates:
            kw = (cand.keyword or '').strip()
            key = kw.lower()
            if not kw or key in seen:
                continue
            seen.add(key)
            cand.keyword = kw
            unique.append(cand)

        if not save:
            return unique

        from strategy.models import DiscoveredKeyword
        saved = []
        for cand in unique:
            obj, _ = DiscoveredKeyword.objects.get_or_create(
                project=project,
                keyword=cand.keyword,
                defaults=dict(
                    source=cand.source,
                    page_source=cand.page_source[:500],
                    confidence=cand.confidence,
                    notes=cand.notes,
                ),
            )
            saved.append(obj)
        return saved
