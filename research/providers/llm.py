"""LLM research provider — synthesizes a content brief via the configured AI
model (SumoPod). Cheap and works today; competitor/heading data is model-
estimated, not live SERP. A real SERP-API provider can replace this later.
"""
from ai_service import generate, pricing

from ..base import ResearchProvider, ResearchResult, ResearchError
from ..prompts import build_research_messages
from ..parsing import extract_json, to_int


def _list(data, key):
    val = data.get(key)
    return val if isinstance(val, list) else []


class LLMResearchProvider(ResearchProvider):
    name = 'llm'

    def research(self, keyword, *, language='id', model=None):
        messages = build_research_messages(keyword, language)
        gen = generate(messages, model=model, max_tokens=2500, temperature=0.4)
        data = extract_json(gen.text)
        if not data:
            raise ResearchError('Hasil research bukan JSON valid.')

        cost = pricing.estimate_text_cost(gen.model, gen.tokens_in, gen.tokens_out)
        return ResearchResult(
            keyword=keyword,
            language=language,
            search_intent=str(data.get('search_intent', '')).strip(),
            intent_note=str(data.get('intent_note', '')).strip(),
            competitors=_list(data, 'competitors'),
            headings=_list(data, 'headings'),
            people_also_ask=_list(data, 'people_also_ask'),
            related_searches=_list(data, 'related_searches'),
            entities=_list(data, 'entities'),
            lsi_keywords=_list(data, 'lsi_keywords'),
            faq=_list(data, 'faq'),
            content_gap=_list(data, 'content_gap'),
            recommended_word_count=to_int(data.get('recommended_word_count')),
            internal_link_opportunities=_list(data, 'internal_link_opportunities'),
            external_reference_opportunities=_list(data, 'external_reference_opportunities'),
            ai_overview_opportunity=str(data.get('ai_overview_opportunity', '')).strip(),
            provider=self.name,
            model_used=gen.model,
            tokens_in=gen.tokens_in,
            tokens_out=gen.tokens_out,
            cost_usd=round(cost, 6),
            duration_ms=gen.duration_ms,
            raw=data,
        )
