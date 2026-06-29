"""Research prompt — asks the model to act as a SERP analyst and return a
structured JSON content brief. Keys here are the single source of truth shared
with the parser/result mapping.

Caveat: with the LLM provider these fields are model-estimated, not live SERP.
A real SERP-API provider can populate the same ResearchResult later.
"""

LANG_NAMES = {"id": "Bahasa Indonesia", "en": "English"}

BRIEF_KEYS = [
    "search_intent", "intent_note", "competitors", "headings", "people_also_ask",
    "related_searches", "entities", "lsi_keywords", "faq", "content_gap",
    "recommended_word_count", "internal_link_opportunities",
    "external_reference_opportunities", "ai_overview_opportunity",
]


def build_research_messages(keyword, language="id"):
    lang = LANG_NAMES.get(language, language)
    system = (
        f"Kamu adalah SEO SERP analyst senior. Lakukan analisis SERP untuk sebuah keyword "
        f"dan hasilkan content brief yang membuat artikel BERPELUANG RANKING di Google "
        f"(Search & AI Overview). Bahasa hasil: {lang}.\n\n"
        "Keluarkan HANYA satu objek JSON valid (tanpa code fence, tanpa teks lain) "
        "dengan kunci berikut:\n"
        "- search_intent: salah satu dari informational/commercial/transactional/navigational\n"
        "- intent_note: 1 kalimat menjelaskan maksud pencari\n"
        "- competitors: array <=10 objek {title, url, angle} (estimasi halaman yang biasa ranking)\n"
        "- headings: array outline H2/H3 yang direkomendasikan (string, prefiks 'H2:'/'H3:')\n"
        "- people_also_ask: array pertanyaan PAA (string)\n"
        "- related_searches: array kata kunci terkait (string)\n"
        "- entities: array entitas penting yang harus disebut (string)\n"
        "- lsi_keywords: array keyword semantik/LSI (string)\n"
        "- faq: array objek {question, answer} (3-6 item)\n"
        "- content_gap: array celah konten yang sering terlewat kompetitor (string)\n"
        "- recommended_word_count: integer perkiraan panjang ideal\n"
        "- internal_link_opportunities: array topik anchor internal (string)\n"
        "- external_reference_opportunities: array sumber otoritatif untuk dirujuk (string)\n"
        "- ai_overview_opportunity: 1-2 kalimat peluang & cara tampil di AI Overview\n"
    )
    user = f"Keyword: {keyword}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
