"""Article quality benchmark — evidence over assumption.

Scores Prompt Builder output across a fixed multi-niche keyword set on a 10-point
checklist so prompt iteration (v3 -> v3.1 -> v3.2) is driven by recurring weakness
data, not feeling.

Most dimensions are scored DETERMINISTICALLY (offline, free, repeatable):
Yoast, readability, repetition, heading, CTA, FAQ, AI-Overview-readiness, and a
human/cliché proxy. The three subjective dimensions — EEAT, semantic depth, and a
deeper human-likeness read — use an optional LLM judge (`run_judge`).

The deterministic scorers are the contract tested in test_benchmark.py; the LLM
judge needs an API key and is exercised only on real runs.
"""
import json
import re
import statistics

from .parsing import slugify
from .seo import score_article


# One representative keyword per niche.
BENCHMARK_KEYWORDS = [
    ("bisnis", "cara memulai bisnis online"),
    ("kesehatan", "cara menurunkan kolesterol secara alami"),
    ("teknologi", "tips memilih laptop untuk programmer"),
    ("otomotif", "cara merawat motor matic"),
    ("pendidikan", "cara belajar efektif untuk ujian"),
    ("wisata", "rekomendasi tempat wisata di bandung"),
    ("kuliner", "resep rendang daging sapi empuk"),
    ("properti", "tips membeli rumah pertama"),
    ("keuangan", "cara mengatur keuangan rumah tangga"),
    ("islami", "tata cara sholat tahajud"),
]

# Mirrors the anti-cliché list the prompt forbids — measures whether the model obeys.
BANNED_CLICHES = [
    "di era digital ini", "tidak dapat dipungkiri", "penting untuk dicatat",
    "mari kita selami", "dalam dunia yang serba cepat", "membuka potensi",
    "sebagai kesimpulan", "di zaman sekarang", "tak bisa dipungkiri",
    "di tengah perkembangan",
]

TRANSITIONS = [
    "selain itu", "namun", "oleh karena itu", "sehingga", "misalnya", "contohnya",
    "pertama", "kedua", "selanjutnya", "akhirnya", "dengan demikian", "sebaliknya",
    "karena itu", "di sisi lain", "sementara itu", "kemudian", "bahkan", "sebagai contoh",
]

CTA_VERBS = [
    "hubungi", "daftar", "kunjungi", "coba", "pelajari", "dapatkan", "beli", "pesan",
    "klik", "ikuti", "konsultasi", "unduh", "mulai", "simak", "kunjungilah",
]

DETERMINISTIC_DIMS = ["yoast", "readability", "repetition", "heading", "cta", "faq", "ai_overview", "human"]
JUDGE_DIMS = ["eeat", "semantic", "human_judge"]


# --- text helpers ---------------------------------------------------------

def _strip(html):
    return re.sub(r"<[^>]+>", " ", html or "")


def _sentences(text):
    return [s.strip() for s in re.split(r"[.!?]+", text or "") if s.strip()]


def _paragraphs(html):
    return [p for p in re.findall(r"<p[^>]*>(.*?)</p>", html or "", re.I | re.S)]


def _headings(html, tag):
    raw = re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", html or "", re.I | re.S)
    return [_strip(h).strip() for h in raw]


def _result(score, notes):
    return {"score": None if score is None else max(0, min(100, round(score))), "notes": notes}


# --- deterministic scorers ------------------------------------------------

def score_readability(html):
    text = _strip(html)
    sents = _sentences(text)
    if not sents:
        return _result(0, ["tidak ada kalimat"])
    words = len(text.split())
    avg = words / len(sents)
    long_ratio = sum(1 for s in sents if len(s.split()) > 25) / len(sents)
    trans = sum(1 for t in TRANSITIONS if t in text.lower())
    notes = []
    score = 100.0
    if avg > 20:
        score -= min(40, (avg - 20) * 5)
        notes.append(f"kalimat rata-rata {avg:.0f} kata (>20)")
    if long_ratio > 0.15:
        score -= min(30, long_ratio * 100)
        notes.append(f"{long_ratio * 100:.0f}% kalimat panjang (>25 kata)")
    if trans < 3:
        score -= 15
        notes.append("transition words minim")
    return _result(score, notes)


def score_repetition(html):
    text = _strip(html).lower()
    words = text.split()
    sents = _sentences(text)
    notes = []
    counts = {}
    for s in sents:
        counts[s] = counts.get(s, 0) + 1
    dup_sentences = sum(c - 1 for c in counts.values() if c > 1)
    tris = [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
    diversity = (len(set(tris)) / len(tris)) if tris else 1.0
    openers = [" ".join(_strip(p).strip().lower().split()[:2]) for p in _paragraphs(html) if _strip(p).strip()]
    opener_dups = len(openers) - len(set(openers))
    score = diversity * 100
    if dup_sentences:
        score -= min(30, dup_sentences * 10)
        notes.append(f"{dup_sentences} kalimat duplikat")
    if opener_dups:
        score -= min(20, opener_dups * 5)
        notes.append(f"{opener_dups} pembuka paragraf berulang")
    if diversity < 0.85:
        notes.append(f"diversitas trigram {diversity * 100:.0f}%")
    return _result(score, notes)


def score_headings(html):
    h2 = _headings(html, "h2")
    h3 = _headings(html, "h3")
    notes = []
    score = 100.0
    if len(h2) < 3:
        score -= 30
        notes.append(f"hanya {len(h2)} H2")
    one_word = [h for h in h2 + h3 if len(h.split()) < 2]
    if one_word:
        score -= 20
        notes.append(f"{len(one_word)} heading satu kata")
    dup = len(h2) - len(set(h.lower() for h in h2))
    if dup:
        score -= 20
        notes.append(f"{dup} H2 duplikat")
    if h3 and not h2:
        score -= 20
        notes.append("ada H3 tanpa H2")
    return _result(score, notes)


def score_cta(html):
    paras = _paragraphs(html)
    tail = " ".join(_strip(p) for p in paras[-2:]).lower() if paras else ""
    has = any(v in tail for v in CTA_VERBS)
    return _result(100 if has else 0, [] if has else ["tidak ada CTA jelas di penutup"])


def score_faq(html):
    low = (html or "").lower()
    has = "faq" in low or "pertanyaan yang sering" in low
    if not has:
        return _result(0, ["tidak ada bagian FAQ"])
    q = sum(1 for h in _headings(html, "h3") if "?" in h)
    notes = []
    score = 100.0
    if q < 3:
        score -= 40
        notes.append(f"hanya {q} pertanyaan FAQ (target 3-5)")
    return _result(score, notes)


def score_ai_overview(html):
    low = (html or "").lower()
    notes = []
    score = 0.0
    if "<ul" in low or "<ol" in low:
        score += 30
    else:
        notes.append("tidak ada list (<ul>/<ol>)")
    if "<table" in low:
        score += 10
    qh = sum(1 for h in _headings(html, "h2") + _headings(html, "h3") if "?" in h)
    if qh >= 2:
        score += 30
    else:
        notes.append("subjudul berbasis pertanyaan minim")
    paras = _paragraphs(html)
    first = _strip(paras[0]) if paras else ""
    if 0 < len(first.split()) <= 50:
        score += 30
    else:
        notes.append("tidak ada jawaban ringkas (answer-first) di awal")
    return _result(score, notes)


def score_human(html):
    text = _strip(html)
    low = text.lower()
    occurrences = sum(low.count(c) for c in BANNED_CLICHES)  # repeated clichés hurt more
    present = [c for c in BANNED_CLICHES if c in low]
    sents = _sentences(text)
    lengths = [len(s.split()) for s in sents]
    burst = statistics.pstdev(lengths) if len(lengths) > 1 else 0
    notes = []
    score = 100.0
    if occurrences:
        score -= min(50, occurrences * 15)
        notes.append("klise AI: " + ", ".join(present))
    if burst < 4:
        score -= 20
        notes.append("variasi panjang kalimat rendah (terasa kaku)")
    return _result(score, notes)


def score_all(keyword, sections, spec):
    """All deterministic dimensions for one parsed article. Returns {dim: {score, notes}}."""
    html = sections.get("ARTICLE_HTML", "")
    yoast = score_article(
        keyword=keyword,
        meta_title=sections.get("META_TITLE", "") or "",
        meta_description=sections.get("META_DESCRIPTION", "") or "",
        slug=sections.get("SLUG", "") or slugify(keyword),
        article_html=html,
        image_alt=sections.get("IMAGE_ALT", "") or "",
        length_target=spec.length,
        faq_required=spec.faq,
        schema_required=spec.schema,
        schema_jsonld=sections.get("SCHEMA_JSONLD", "") or "",
    )
    return {
        "yoast": _result(yoast["score"], yoast["failures"]),
        "readability": score_readability(html),
        "repetition": score_repetition(html),
        "heading": score_headings(html),
        "cta": score_cta(html),
        "faq": score_faq(html) if spec.faq else _result(None, []),
        "ai_overview": score_ai_overview(html),
        "human": score_human(html),
    }


# --- LLM judge (subjective dims) ------------------------------------------

def build_judge_messages(article_html):
    system = (
        "Kamu adalah juri kualitas konten SEO yang ketat. Nilai artikel HTML berikut pada 3 dimensi, "
        "skala 0-100, dan beri satu catatan singkat per dimensi.\n"
        "- eeat: bukti keahlian, akurasi, kedalaman 'mengapa', kepercayaan.\n"
        "- semantic: cakupan entitas/sub-topik, kelengkapan semantik, kedalaman topikal.\n"
        "- human: terasa ditulis manusia ahli (bukan AI), natural, tidak repetitif/klise.\n"
        'Keluarkan HANYA JSON valid: {"eeat":{"score":N,"note":"..."},'
        '"semantic":{"score":N,"note":"..."},"human":{"score":N,"note":"..."}}'
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": article_html[:12000]},
    ]


def run_judge(generate_fn, article_html):
    """Score eeat/semantic/human via an LLM. Returns {} on any failure (judge is optional)."""
    try:
        raw = generate_fn(build_judge_messages(article_html), max_tokens=400, temperature=0.0).text
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        out = {}
        for dim, key in [("eeat", "eeat"), ("semantic", "semantic"), ("human_judge", "human")]:
            d = data.get(key) or {}
            out[dim] = _result(d.get("score"), [d.get("note", "")] if d.get("note") else [])
        return out
    except Exception:
        return {}


# --- aggregation & report -------------------------------------------------

def aggregate(results):
    """Average each dimension across articles and rank weakest-first."""
    dims = DETERMINISTIC_DIMS + JUDGE_DIMS
    averages = {}
    note_freq = {}
    for dim in dims:
        scores = [r["scores"][dim]["score"] for r in results
                  if dim in r["scores"] and r["scores"][dim]["score"] is not None]
        if not scores:
            continue
        averages[dim] = round(sum(scores) / len(scores), 1)
        freq = {}
        for r in results:
            for note in r["scores"].get(dim, {}).get("notes", []):
                key = re.sub(r"\d+", "N", note)  # normalise numbers to cluster notes
                freq[key] = freq.get(key, 0) + 1
        note_freq[dim] = sorted(freq.items(), key=lambda x: -x[1])
    ranked = sorted(averages.items(), key=lambda x: x[1])
    return {"averages": averages, "ranked": ranked, "note_freq": note_freq, "n": len(results)}


def render_report(meta, results, agg):
    lines = [
        f"# Benchmark kualitas artikel — {meta.get('prompt_version', '?')}",
        "",
        f"- Waktu: {meta.get('timestamp')}",
        f"- Artikel: {agg['n']} keyword · model: {meta.get('model', '?')} · length target: {meta.get('length')}",
        f"- Judge LLM: {'ya' if meta.get('judge') else 'tidak'}",
        "",
        "## Skor rata-rata per dimensi (terlemah di atas)",
        "",
        "| Dimensi | Rata-rata |",
        "|---|---|",
    ]
    for dim, avg in agg["ranked"]:
        lines.append(f"| {dim} | {avg} |")
    lines += ["", "## Skor per artikel", "", "| niche | keyword | overall | " + " | ".join(DETERMINISTIC_DIMS) + " |",
              "|---|---|---|" + "---|" * len(DETERMINISTIC_DIMS)]
    for r in results:
        cells = []
        for dim in DETERMINISTIC_DIMS:
            s = r["scores"].get(dim, {}).get("score")
            cells.append("-" if s is None else str(s))
        lines.append(f"| {r['niche']} | {r['keyword']} | {r['overall']} | " + " | ".join(cells) + " |")
    lines += ["", "## Kelemahan berulang (kandidat iterasi prompt)", ""]
    for dim, avg in agg["ranked"]:
        if avg >= 85:
            continue
        top = agg["note_freq"].get(dim, [])[:3]
        if not top:
            continue
        lines.append(f"- **{dim}** (avg {avg}): " + "; ".join(f"{note} (x{n})" for note, n in top))
    lines.append("")
    return "\n".join(lines)


def overall_score(scores):
    vals = [v["score"] for v in scores.values() if v["score"] is not None]
    return round(sum(vals) / len(vals), 1) if vals else 0.0
