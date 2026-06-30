"""Keyword data provider (volume/difficulty/cpc) — the A-ready slot.

Default = NullKeywordDataProvider: metrics stay None (NEVER fabricated). A real
DataForSEO/Serper provider plugs in here later via KEYWORD_DATA_PROVIDER, with
no change to business logic.
"""
from abc import ABC, abstractmethod

from decouple import config


class KeywordDataProvider(ABC):
    name = 'base'

    @abstractmethod
    def enrich(self, keyword) -> dict:
        """Return {volume, difficulty, cpc, intent} — None for any unknown value."""


class NullKeywordDataProvider(KeywordDataProvider):
    name = 'null'

    def enrich(self, keyword):
        # No real data source configured → nothing is fabricated.
        return {'volume': None, 'difficulty': None, 'cpc': None, 'intent': None}


def get_keyword_data_provider(name=None):
    name = name or config('KEYWORD_DATA_PROVIDER', default='null')
    if name == 'null':
        return NullKeywordDataProvider()
    if name == 'dataforseo':
        raise NotImplementedError("DataForSEO provider belum diimplementasikan.")
    raise ValueError(f"Unknown KEYWORD_DATA_PROVIDER: {name!r}")


def enrich_keywords(project, provider=None):
    """Fill real metrics from a data provider. The null provider leaves them None."""
    from strategy.models import DiscoveredKeyword

    provider = provider or get_keyword_data_provider()
    updated = 0
    for dk in DiscoveredKeyword.objects.filter(project=project):
        data = provider.enrich(dk.keyword) or {}
        changed = False
        for field in ('volume', 'difficulty', 'cpc'):
            val = data.get(field)
            if val is not None:
                setattr(dk, field, val)
                changed = True
        intent = data.get('intent')
        if intent and not dk.intent:
            dk.intent = intent
            changed = True
        if changed:
            dk.save(update_fields=['volume', 'difficulty', 'cpc', 'intent'])
            updated += 1
    return updated
