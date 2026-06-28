"""Prompt Builder — the core product asset.

Assembles the article/title prompts compositionally from a structured spec, so
prompt quality can be improved here WITHOUT touching views, tasks, or engines.
Versioned (PROMPT_VERSION) for A/B and rollback.

The article prompt instructs the model to emit a strict sentinel-delimited
block (not JSON) — robust for large HTML payloads. `OUTPUT_SECTIONS` is the
single source of truth shared with the parser in the generator task.
"""
from dataclasses import dataclass, field

PROMPT_VERSION = "article_v2"

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
    brand_voice: str = ""
    length: int = 1500
    cta: str = ""
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
                              cta=None, faq=True, internal_links=None,
                              external_links=None, schema=True, ai_overview=True,
                              yoast=True):
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
        brand_voice=project.brand_voice,
        length=length or project.default_length,
        cta=cta if cta is not None else project.default_cta,
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
            "- Readability: paragraf pendek (2-4 kalimat), kalimat ringkas, gunakan transition words, "
            "distribusikan subjudul merata.",
        ]
    if spec.ai_overview:
        rules += [
            "- Optimasi Google AI Overview: beri jawaban langsung & ringkas di dekat awal "
            "(answer-first / poin kunci), pakai subjudul berbasis pertanyaan, dan lengkapi cakupan entitas/sub-topik.",
            "- Manfaatkan <ul>/<ol>/<table> untuk informasi yang cocok disajikan terstruktur.",
        ]
    return "\n".join(rules)


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


def build_article_messages(spec: ArticleSpec):
    """Assemble the chat messages for one SEO article generation."""
    skeleton = STYLE_SKELETONS.get(spec.writing_style, STYLE_SKELETONS["blog"])

    system_parts = [
        f"Kamu adalah SEO content strategist & penulis profesional. Tulis artikel SEO BERKUALITAS "
        f"(bukan sekadar artikel AI) dalam {spec.lang_name}.",
        f"Tone: {spec.tone}. Target pembaca: {spec.target_audience or 'pembaca umum'}.",
    ]
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

    system_parts.append("ATURAN SEO:\n" + _seo_rules(spec))
    system_parts.append("ATURAN LINK:\n" + _link_rules(spec))

    if spec.faq:
        system_parts.append("Sertakan bagian FAQ (3-5 pertanyaan) dengan subjudul <h2>FAQ</h2> dan pertanyaan <h3>.")
    if spec.cta:
        system_parts.append(f"Akhiri dengan call-to-action: {spec.cta}")

    system_parts.append(_output_contract(spec))

    user = f"Keyword utama: {spec.keyword}"
    if spec.title:
        user += f"\nJudul: {spec.title}"
    user += "\n\nTulis artikel lengkap sekarang dalam format output yang diminta."

    return [
        {"role": "system", "content": "\n\n".join(system_parts)},
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
