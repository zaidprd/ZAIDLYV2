"""Mock AI provider — run the whole product end-to-end without an API key.

Set `AI_PROVIDER=mock` to make generation/publish work offline for development,
demos, and integration tests. It returns a deterministic, well-formed article in
the exact sentinel format the parser expects (so it passes the quality gate), plus
a placeholder image URL. Swap back to `openai_compatible` once a real key exists —
no other code changes.
"""
import re

from ai_service.base import AIProvider, GenerationResult


def _keyword(user_msg):
    m = re.search(r"Keyword utama:\s*(.+)", user_msg or "")
    return (m.group(1).splitlines()[0].strip() if m else "topik ini") or "topik ini"


def _mock_titles(user_msg):
    kw = _keyword(user_msg)
    base = [
        f"Panduan Lengkap {kw} untuk Pemula",
        f"7 Tips {kw} yang Wajib Diketahui",
        f"Cara {kw} dengan Mudah dan Cepat",
        f"Kesalahan Umum dalam {kw} dan Solusinya",
        f"{kw}: Apa yang Perlu Anda Pahami",
    ]
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(base))


def _mock_article(user_msg):
    kw = _keyword(user_msg)
    title = kw.capitalize()
    return f"""<<<META_TITLE>>>
Panduan {title} Lengkap untuk Pemula
<<<META_DESCRIPTION>>>
Pelajari {kw} dari dasar: langkah praktis, tips, dan jawaban pertanyaan umum dalam panduan ringkas ini.
<<<SLUG>>>
{re.sub(r'[^a-z0-9]+', '-', kw.lower()).strip('-')}
<<<IMAGE_PROMPT>>>
Editorial photo illustrating {kw}, clean modern style, natural light, no text overlay.
<<<IMAGE_ALT>>>
Ilustrasi untuk {kw}
<<<ARTICLE_HTML>>>
<p>{title} adalah hal yang bisa dipelajari siapa saja. Artikel ini merangkum langkah inti {kw} secara ringkas dan praktis.</p>
<h2>Apa itu {kw}?</h2><p>Secara singkat, {kw} adalah proses yang bisa dijalankan bertahap. Pahami dasarnya dulu sebelum melangkah lebih jauh.</p>
<h2>Bagaimana langkah memulai {kw}?</h2><p>Mulai dari persiapan, lalu eksekusi bertahap. Berikut urutan yang mudah diikuti.</p><ul><li>Tentukan tujuan</li><li>Siapkan kebutuhan dasar</li><li>Jalankan langkah pertama</li><li>Evaluasi hasil</li></ul>
<h2>Tips agar {kw} lebih efektif</h2><p>Konsistensi lebih penting daripada kesempurnaan. Selain itu, catat progres agar mudah dievaluasi.</p>
<h2>Kesalahan umum yang perlu dihindari</h2><p>Banyak pemula terburu-buru. Sebaliknya, lakukan langkah kecil yang konsisten agar hasilnya bertahan.</p>
<h2>FAQ</h2><h3>Apakah {kw} cocok untuk pemula?</h3><p>Ya, selama mengikuti langkah dasar dengan sabar.</p><h3>Berapa lama hasil terlihat?</h3><p>Bergantung konsistensi, umumnya beberapa minggu.</p><h3>Perlu biaya besar?</h3><p>Tidak harus; bisa dimulai dengan sumber daya seadanya.</p>
<p>Siap mempraktikkan {kw}? Pelajari selengkapnya dan mulai langkah pertama Anda hari ini.</p>
<<<SCHEMA_JSONLD>>>
{{"@context":"https://schema.org","@type":"Article","headline":"Panduan {title}"}}
<<<END>>>"""


class MockProvider(AIProvider):
    """Deterministic offline provider. No network, no key."""

    def complete(self, messages, *, model=None, temperature=0.7, max_tokens=4000, timeout=120):
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"] if messages else ""
        # The article prompt carries the sentinel output contract; titles prompt does not.
        is_article = "<<<META_TITLE>>>" in system
        text = _mock_article(user) if is_article else _mock_titles(user)
        return GenerationResult(
            text=text, model=model or "mock", tokens_in=1200, tokens_out=2400, duration_ms=1500,
        )

    def generate_image(self, prompt, *, model=None, size="1024x1024"):
        return "https://placehold.co/1024x576/png?text=Featured+Image"
