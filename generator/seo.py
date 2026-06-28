"""SEO scorer / quality gate (PRD §5).

`score_article` runs the full checklist and returns a score plus structured
failures. The failures feed the auto-revision loop (the model is asked to fix
exactly what failed) and are surfaced to the user as the SEO score.
"""
import re

DEFAULT_THRESHOLD = 70


def _strip(html):
    return re.sub(r"<[^>]+>", " ", html or "")


def score_article(*, keyword, meta_title, meta_description, slug, article_html,
                  image_alt="", length_target=1500, faq_required=True,
                  schema_required=True, schema_jsonld="", threshold=DEFAULT_THRESHOLD):
    kw = (keyword or "").lower().strip()
    html_lower = (article_html or "").lower()
    plain = _strip(article_html)
    words = plain.split()
    word_count = len(words)

    checks = []

    def check(label, passed, tip=""):
        checks.append({"label": label, "passed": bool(passed), "tip": tip})

    # Keyword placement
    check("Keyword di meta title", kw in (meta_title or "").lower(),
          "Masukkan keyword utama ke meta title.")
    first_p = re.search(r"<p[^>]*>(.*?)</p>", article_html or "", re.IGNORECASE | re.DOTALL)
    first_p_text = _strip(first_p.group(1)).lower() if first_p else ""
    check("Keyword di paragraf pertama", kw in first_p_text,
          "Sebutkan keyword di paragraf pembuka.")
    h2_texts = re.findall(r"<h2[^>]*>(.*?)</h2>", article_html or "", re.IGNORECASE | re.DOTALL)
    check("Keyword di salah satu H2", any(kw in _strip(h).lower() for h in h2_texts),
          "Sertakan keyword di minimal satu subjudul H2.")
    check("Keyword di alt text gambar", kw in (image_alt or "").lower(),
          "Tambahkan keyword pada alt text gambar.")

    # Keyword density
    occ = len(re.findall(re.escape(kw), plain.lower())) if kw else 0
    kw_words = len(kw.split()) or 1
    density = round((occ * kw_words) / word_count * 100, 2) if word_count else 0.0
    check("Densitas keyword 0.5-2.5%", 0.5 <= density <= 2.5,
          f"Densitas {density}%. Jaga di rentang 0.5-2.5% (natural).")

    # Meta
    check("Meta title <= 60 karakter", bool(meta_title) and len(meta_title) <= 60,
          "Meta title idealnya <= 60 karakter.")
    check("Meta description 50-155 karakter",
          bool(meta_description) and 50 <= len(meta_description) <= 155,
          "Meta description idealnya 50-155 karakter.")

    # Slug
    check("Slug valid", bool(slug) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug or "") is not None,
          "Slug harus kebab-case (huruf kecil, tanpa spasi).")

    # Structure
    h2_count = len(re.findall(r"<h2", html_lower))
    check("Minimal 2 heading H2", h2_count >= 2,
          f"Hanya {h2_count} H2. Tambahkan sub-bagian.")
    check(f"Panjang artikel >= {int(length_target * 0.8)} kata",
          word_count >= length_target * 0.8,
          f"Baru {word_count} kata; target ~{length_target}.")

    # Readability (light): average sentence length
    sentences = [s for s in re.split(r"[.!?]+", plain) if s.strip()]
    avg_sentence = (word_count / len(sentences)) if sentences else 0
    check("Keterbacaan (kalimat <= 25 kata rata-rata)", avg_sentence <= 25,
          f"Rata-rata {round(avg_sentence)} kata/kalimat. Pecah kalimat panjang.")

    # FAQ / schema (conditional)
    if faq_required:
        check("Ada bagian FAQ", "faq" in html_lower, "Tambahkan bagian FAQ.")
    if schema_required:
        check("Schema JSON-LD ada", bool((schema_jsonld or "").strip()),
              "Sertakan schema JSON-LD (Article/FAQPage).")

    passed_count = sum(1 for c in checks if c["passed"])
    score = round((passed_count / len(checks)) * 100) if checks else 0
    failures = [c["tip"] for c in checks if not c["passed"] and c["tip"]]

    return {
        "score": score,
        "passed": score >= threshold,
        "threshold": threshold,
        "checks": checks,
        "failures": failures,
        "word_count": word_count,
        "keyword_density": density,
        "h2_count": h2_count,
    }


def validate(keyword, title, article_html, meta_description):
    """Backward-compatible shim used by older callers."""
    return score_article(
        keyword=keyword, meta_title=title, meta_description=meta_description,
        slug="", article_html=article_html, faq_required=False, schema_required=False,
    )
