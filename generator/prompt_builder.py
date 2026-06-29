"""Prompt Builder — the core product asset.

Assembles the article/title prompts compositionally from a structured spec, so
prompt quality can be improved here WITHOUT touching views, tasks, or engines.
Versioned (PROMPT_VERSION) for A/B and rollback.

The article prompt instructs the model to emit a strict sentinel-delimited
block (not JSON) — robust for large HTML payloads. `OUTPUT_SECTIONS` is the
single source of truth shared with the parser in the generator task.
"""
from dataclasses import dataclass, field

PROMPT_VERSION = "article_v3"

# Ordered output sections. The parser splits the model output on `<<<NAME>>>`.
OUTPUT_SECTIONS = [
    "META_TITLE",
    "META_DESCRIPTION",
    "SLUG",
    "IMAGE_PROMPT",
    "IMAGE_ALT",
    "ARTICLE_HTML",
    "SCHEMA_JSONLD",
]

ALLOWED_TAGS = "h2, h3, p, ul, ol, li, strong, em, table, thead, tbody, tr, th, td, blockquote, a"

# Per-style skeletons keep each writing style structurally distinct.
STYLE_SKELETONS = {
    "blog": "Intro hook → 5-7 bagian <h2> bertema → kesimpulan ringkas.",
    "review": "Ringkasan verdict di awal → fitur/aspek (<h2>) → kelebihan & kekurangan (<ul>) → verdict akhir.",
    "tutorial": "Prasyarat → langkah berurutan ber-<h2>/<h3> (mudah diikuti) → tips/troubleshooting.",
    "listicle": "Intro singkat → N item bernomor sebagai <h2> → ringkasan penutup.",
    "evergreen": "Definisi/jawaban inti → konteks mendalam → praktik terbaik → FAQ.",
    "news": "Inverted pyramid: inti berita di paragraf awal → detail → konteks pendukung.",
}

LANG_NAMES = {"id": "Bahasa Indonesia", "en": "English"}


@dataclass
class ArticleSpec:
    """Everything the Prompt Builder needs to assemble an article prompt."""

    keyword: str
    title: str = ""
    secondary_keywords: list = field(default_factory=list)
    lsi_keywords: list = field(default_factory=list)
    language: str = "id"
    tone: str = "informative"
    writing_style: str = "blog"
    target_audience: str = ""
    goal: str = ""                  # tujuan artikel: inform / convert / rank / educate ...
    brand_voice: str = ""
    length: int = 1500
    cta: str = ""
    image_style: str = ""           # steer the featured-image prompt
    faq: bool = True
    internal_links: list = field(default_factory=list)
    external_links: list = field(default_factory=list)
    schema: bool = True
    ai_overview: bool = True
    yoast: bool = True

    @property
    def lang_name(self):
        return LANG_NAMES.get(self.language, self.language)

    @property
    def length_label(self):
        return "5000+ kata" if self.length >= 5000 else f"{self.length} kata"


def article_spec_from_project(project, *, keyword, title="", secondary_keywords=None,
                              lsi_keywords=None, length=None, writing_style=None,
                              goal=None, cta=None, image_style=None, faq=True,
                              internal_links=None, external_links=None, schema=True,
                              ai_overview=True, yoast=True):
    """Build an ArticleSpec from a Project + per-generation overrides."""
    return ArticleSpec(
        keyword=keyword,
        title=title,
        secondary_keywords=secondary_keywords or [],
        lsi_keywords=lsi_keywords or [],
        language=project.language,
        tone=project.get_tone_display(),
        writing_style=writing_style or project.writing_style,
        target_audience=project.target_audience or "pembaca umum",
        goal=goal or "",
        brand_voice=project.brand_voice,
        length=length or project.default_length,
        cta=cta if cta is not None else project.default_cta,
        image_style=image_style or "",
        faq=faq,
        internal_links=internal_links or [],
        external_links=external_links or [],
        schema=schema,
        ai_overview=ai_overview,
        yoast=yoast,
    )


def _join(label, items):
    return f"{label}: {', '.join(items)}" if items else ""


def _seo_rules(spec):
    """Yoast / keyword placement rules."""
    rules = [
        f"- Keyword utama '{spec.keyword}' WAJIB muncul di: meta title, meta description, slug, "
        "kalimat pertama paragraf pembuka, minimal satu subjudul <h2>, dan alt text gambar.",
        "- Densitas keyword utama natural (~0.5-2.5%), jangan keyword stuffing.",
    ]
    if spec.secondary_keywords:
        rules.append("- Sisipkan secondary keyword secara natural di subjudul & body.")
    if spec.lsi_keywords:
        rules.append("- Gunakan LSI keyword untuk memperkaya cakupan semantik.")
    if spec.yoast:
        rules += [
            "- Meta title ≤ 60 karakter; meta description ≤ 155 karakter dengan ajakan membaca.",
            "- Readability ala Yoast: paragraf pendek (2-4 kalimat), mayoritas kalimat < 20 kata, "
            "gunakan transition words, dan beri subjudul tiap ~300 kata.",
        ]
    return "\n".join(rules)


def _ai_overview_rules(spec):
    """Google AI Overview optimisation — gated so it disappears when toggled off."""
    if not spec.ai_overview:
        return ""
    return (
        "OPTIMASI GOOGLE AI OVERVIEW:\n"
        "- Beri jawaban langsung & ringkas (2-3 kalimat) tepat di bawah subjudul kunci sebelum penjelasan panjang (answer-first).\n"
        "- Gunakan subjudul berbentuk pertanyaan pada bagian yang relevan.\n"
        "- Sajikan fakta terstruktur dengan <ul>/<ol>/<table> agar mudah dikutip mesin.\n"
        "- Lengkapi cakupan entitas & sub-topik turunan agar dianggap sumber paling komprehensif."
    )


def _quality_rules(spec):
    """Premium quality bar — the product's real differentiator.

    Deliberately free of the words 'FAQ' and 'AI Overview' so it stays visible
    even when those toggles are off.
    """
    return (
        "STANDAR KUALITAS (WAJIB — ini pembeda produk):\n"
        "EEAT:\n"
        "- Tunjukkan keahlian nyata: detail spesifik, angka, contoh konkret, langkah praktis — bukan generalisasi.\n"
        "- Akurasi faktual: JANGAN mengarang statistik, kutipan, tanggal, atau nama sumber. Bila tak pasti, pakai bahasa hati-hati.\n"
        "- Jelaskan 'mengapa' di balik klaim (alasan/mekanisme), bukan hanya 'apa'.\n"
        "- Seimbang & jujur: sebut trade-off/keterbatasan bila relevan; hindari hype berlebihan.\n"
        "SEMANTIC SEO:\n"
        "- Cakupan menyeluruh: bahas entitas, sinonim, dan sub-pertanyaan terkait secara natural, bukan sekadar keyword.\n"
        "- Tiap bagian menambah informasi BARU dan saling terhubung agar terasa utuh & mendalam.\n"
        "KUALITAS MANUSIA & ANTI-REPETISI:\n"
        "- Tulis seperti pakar manusia berpengalaman. Variasikan panjang & struktur kalimat; pakai kalimat aktif & langsung.\n"
        "- DILARANG frasa klise AI: 'di era digital ini', 'tidak dapat dipungkiri', 'penting untuk dicatat', "
        "'mari kita selami', 'dalam dunia yang serba cepat', 'membuka potensi', 'sebagai kesimpulan'.\n"
        "- DILARANG mengulang gagasan, kalimat, atau pola pembuka paragraf yang mirip. Setiap paragraf unik, tanpa kalimat pengisi.\n"
        "HEADING:\n"
        "- Heading deskriptif & spesifik (bukan satu kata), hierarki H2>H3 rapi & paralel, keyword natural (tidak dijejalkan)."
    )


def _link_rules(spec):
    parts = []
    if spec.internal_links:
        parts.append(_join("Internal link (sisipkan kontekstual, gunakan PERSIS URL ini)", spec.internal_links))
    if spec.external_links:
        parts.append(_join("External link otoritatif (sisipkan kontekstual)", spec.external_links))
    # Hard guardrail: never fabricate links/slugs.
    parts.append("- JANGAN mengarang internal link, URL, atau slug. Hanya gunakan link yang diberikan di atas; "
                 "jika tidak ada yang diberikan, jangan menambahkan link internal sama sekali.")
    return "\n".join(p for p in parts if p)


def _output_contract(spec):
    schema_line = (
        "JSON-LD valid (Article" + (" + FAQPage" if spec.faq else "") + "), tanpa tag <script>"
        if spec.schema else "kosongkan (tidak diminta)"
    )
    return (
        "FORMAT OUTPUT — keluarkan PERSIS blok berikut, tanpa teks lain, tanpa code fence:\n"
        "<<<META_TITLE>>>\n(meta title ≤60 karakter)\n"
        "<<<META_DESCRIPTION>>>\n(meta description ≤155 karakter)\n"
        "<<<SLUG>>>\n(slug-url-kebab-case, fokus keyword)\n"
        "<<<IMAGE_PROMPT>>>\n(prompt deskriptif untuk featured image, tanpa teks di gambar)\n"
        "<<<IMAGE_ALT>>>\n(alt text gambar, deskriptif & sadar-keyword)\n"
        "<<<ARTICLE_HTML>>>\n(artikel dalam HTML; hanya tag: " + ALLOWED_TAGS + "; tanpa <h1>/<html>/<body>)\n"
        "<<<SCHEMA_JSONLD>>>\n(" + schema_line + ")\n"
        "<<<END>>>"
    )


def _research_block(brief):
    """Inject SERP research so the article is written FROM data, not from memory.

    Returns '' for an empty/stub brief, keeping behaviour identical until real
    SERP grounding is wired in.
    """
    if brief is None or not getattr(brief, "is_grounded", False):
        return ""
    parts = ["RISET SERP (dasar penulisan — kalahkan pesaing dengan kelengkapan):"]
    if brief.subtopics_required:
        parts.append("- Sub-topik yang WAJIB dibahas: " + "; ".join(brief.subtopics_required))
    if brief.entities:
        parts.append("- Entity yang harus disebut: " + ", ".join(brief.entities))
    if brief.paa:
        parts.append("- Jawab pertanyaan People Also Ask ini: " + " | ".join(brief.paa))
    if brief.semantic_keywords:
        parts.append("- Sisipkan secara natural semantic keyword: " + ", ".join(brief.semantic_keywords))
    if brief.median_word_count:
        parts.append(f"- Panjang pesaing rata-rata ~{brief.median_word_count} kata; lampaui kelengkapannya.")
    return "\n".join(parts)


def build_article_messages(spec: ArticleSpec, brief=None):
    """Assemble the chat messages for one SEO article generation.

    `brief` (research.brief.ContentBrief) grounds the article in SERP findings
    when present; omitted/empty -> classic behaviour.
    """
    skeleton = STYLE_SKELETONS.get(spec.writing_style, STYLE_SKELETONS["blog"])

    system_parts = [
        f"Kamu adalah SEO content strategist & penulis senior kelas dunia. Tulis artikel SEO PREMIUM "
        f"berkualitas manusia (tak terbedakan dari tulisan pakar) dalam {spec.lang_name} — bukan sekadar artikel AI.",
        f"Tone: {spec.tone}. Target pembaca: {spec.target_audience or 'pembaca umum'}.",
    ]
    if spec.goal:
        system_parts.append(f"Tujuan artikel: {spec.goal}. Selaraskan sudut pandang, kedalaman, dan CTA dengan tujuan ini.")
    if spec.brand_voice:
        system_parts.append(f"Brand voice: {spec.brand_voice}.")

    system_parts.append(f"Panjang target: {spec.length_label}. Tulis lengkap dan tuntas, jangan dipotong.")
    system_parts.append(f"Bentuk artikel ({spec.writing_style}): {skeleton}")

    kw = _join("Secondary keyword", spec.secondary_keywords)
    lsi = _join("LSI keyword", spec.lsi_keywords)
    if kw:
        system_parts.append(kw)
    if lsi:
        system_parts.append(lsi)

    research = _research_block(brief)
    if research:
        system_parts.append(research)

    system_parts.append("ATURAN SEO:\n" + _seo_rules(spec))
    ai_overview = _ai_overview_rules(spec)
    if ai_overview:
        system_parts.append(ai_overview)
    system_parts.append(_quality_rules(spec))
    system_parts.append("ATURAN LINK:\n" + _link_rules(spec))

    if spec.faq:
        system_parts.append("Sertakan bagian FAQ (3-5 pertanyaan unik yang benar-benar ditanyakan pembaca) "
                            "dengan subjudul <h2>FAQ</h2> dan tiap pertanyaan sebagai <h3>; jawaban ringkas & langsung.")
    if spec.cta:
        system_parts.append(f"Akhiri dengan call-to-action yang halus & relevan: {spec.cta}")

    img_dir = spec.image_style or "gaya editorial modern, realistis, relevan dengan topik"
    system_parts.append(f"Arahan featured image: {img_dir}. Prompt gambar harus deskriptif & spesifik, tanpa teks di gambar.")

    system_parts.append(_output_contract(spec))

    user = f"Keyword utama: {spec.keyword}"
    if spec.title:
        user += f"\nJudul: {spec.title}"
    user += "\n\nTulis artikel lengkap sekarang dalam format output yang diminta. Patuhi STANDAR KUALITAS di atas."

    return [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": user},
    ]


def build_revision_messages(spec: ArticleSpec, previous_output: str, failures):
    """Ask the model to FIX specific SEO issues, re-emitting the full output block."""
    issues = "\n".join(f"- {f}" for f in failures)
    system = (
        "Kamu adalah SEO editor senior. Perbaiki artikel berikut agar lolos standar SEO TANPA menurunkan kualitas. "
        "Pertahankan gaya manusia & EEAT; jangan menambah repetisi atau frasa klise AI; jangan kurangi panjang. "
        "Keluarkan ULANG seluruh blok output dengan format penanda yang SAMA PERSIS "
        "(<<<META_TITLE>>> ... <<<END>>>), tanpa teks lain."
    )
    user = (
        f"Keyword utama: {spec.keyword}\n\n"
        f"Masalah SEO yang HARUS diperbaiki:\n{issues}\n\n"
        f"Artikel saat ini:\n{previous_output}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_titles_messages(keyword, *, language="id", tone="informative",
                          target_audience="", writing_style="blog", count=15):
    """Assemble chat messages for SEO title generation."""
    lang = LANG_NAMES.get(language, language)
    audience = target_audience or "pembaca umum"
    return [
        {
            "role": "system",
            "content": (
                f"Kamu adalah spesialis SEO. Buat {count} judul artikel SEO yang menarik dan layak-klik "
                f"untuk gaya {writing_style}.\n"
                f"Bahasa: {lang}. Tone: {tone}. Target pembaca: {audience}.\n"
                "Aturan:\n"
                "- Setiap judul mengandung keyword utama.\n"
                "- Variasikan: How-to, List, Ultimate Guide, Pertanyaan, dll.\n"
                "- Panjang 40-70 karakter.\n"
                "- Tulis HANYA daftar bernomor, tidak ada teks lain."
            ),
        },
        {"role": "user", "content": f"Keyword: {keyword}"},
    ]


def build_image_prompt(keyword, title="", style_hint=""):
    """Featured-image prompt (fallback when the article output omits one)."""
    base = (
        f"Professional featured image for an article about '{keyword}'. "
        "Clean, modern, editorial style. No text overlay. High-quality photography look."
    )
    return f"{base} {style_hint}".strip()
