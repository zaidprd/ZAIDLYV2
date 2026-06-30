"""Run the article quality benchmark across niches.

    manage.py benchmark --dry              # self-test, no API calls
    manage.py benchmark                     # real generation (needs AI_API_KEY)
    manage.py benchmark --judge             # + LLM judge for EEAT/semantic/human
    manage.py benchmark --limit 3 --length 1500 --model gpt-4o-mini

Outputs per run:
    benchmarks/runs/<ts>/<niche>_<slug>.json   raw output + scores + telemetry
    benchmarks/reports/report-<ts>.md          committable evidence + weaknesses
"""
import datetime
import json
import os

from django.core.management.base import BaseCommand

from ai_service import generate as ai_generate
from ai_service import pricing
from generator import benchmark as bm
from generator.parsing import parse_article_output, slugify
from generator.prompt_builder import ArticleSpec, build_article_messages, PROMPT_VERSION


# A canned article (with deliberate flaws) so --dry exercises the scorers offline.
DRY_SAMPLE = """<<<META_TITLE>>>
Cara Memulai Bisnis Online untuk Pemula
<<<META_DESCRIPTION>>>
Panduan cara memulai bisnis online dari nol, mulai dari ide, modal, sampai pemasaran pertama Anda.
<<<SLUG>>>
cara-memulai-bisnis-online
<<<IMAGE_PROMPT>>>
A tidy home office with a laptop showing an online store, editorial style, no text.
<<<IMAGE_ALT>>>
Meja kerja untuk memulai bisnis online
<<<ARTICLE_HTML>>>
<p>Cara memulai bisnis online tidak serumit yang dibayangkan. Anda bisa mulai dari rumah dengan modal kecil.</p>
<h2>Apa itu bisnis online</h2><p>Bisnis online adalah usaha yang berjalan lewat internet. Modelnya beragam, dari toko produk hingga jasa.</p>
<h2>Bagaimana memilih produk</h2><p>Pilih produk yang Anda pahami. Selain itu, periksa permintaan pasar lewat tren pencarian.</p><ul><li>Riset kebutuhan</li><li>Cek pesaing</li><li>Hitung margin</li></ul>
<h2>Berapa modal yang dibutuhkan</h2><p>Modal bergantung pada model bisnis. Untuk dropship, modal bisa di bawah satu juta rupiah.</p>
<h2>FAQ</h2><h3>Apakah bisnis online butuh modal besar?</h3><p>Tidak. Banyak model bisa dimulai dengan modal kecil.</p><h3>Berapa lama sampai untung?</h3><p>Bervariasi, umumnya beberapa bulan dengan konsistensi.</p>
<p>Pelajari selengkapnya panduan lanjutan di situs kami dan mulai langkah pertama Anda.</p>
<<<SCHEMA_JSONLD>>>
{"@context":"https://schema.org","@type":"Article"}
<<<END>>>"""


class Command(BaseCommand):
    help = "Benchmark article quality across niches (deterministic + optional LLM judge)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Only the first N keywords.")
        parser.add_argument("--length", type=int, default=1500)
        parser.add_argument("--model", default="", help="Override AI_DEFAULT_MODEL.")
        parser.add_argument("--judge", action="store_true", help="Add LLM judge (EEAT/semantic/human).")
        parser.add_argument("--dry", action="store_true", help="No API calls; canned article.")
        parser.add_argument("--out", default="benchmarks")

    def handle(self, *args, **opts):
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        keywords = bm.BENCHMARK_KEYWORDS[:opts["limit"]] if opts["limit"] else bm.BENCHMARK_KEYWORDS
        run_dir = os.path.join(opts["out"], "runs", ts)
        rep_dir = os.path.join(opts["out"], "reports")
        os.makedirs(run_dir, exist_ok=True)
        os.makedirs(rep_dir, exist_ok=True)

        results = []
        total_cost = 0.0
        for niche, kw in keywords:
            spec = ArticleSpec(
                keyword=kw, length=opts["length"], writing_style="blog", tone="informatif",
                target_audience="pembaca umum", cta="Pelajari selengkapnya di situs kami",
                faq=True, schema=True, ai_overview=True, yoast=True,
            )
            messages = build_article_messages(spec)

            if opts["dry"]:
                text, model, t_in, t_out, dur = DRY_SAMPLE, "dry", 0, 0, 0
            else:
                max_tok = min(int(opts["length"] * 2.2) + 800, 16000)
                gen = ai_generate(messages, model=opts["model"] or None, max_tokens=max_tok, temperature=0.6)
                text, model = gen.text, gen.model
                t_in, t_out, dur = gen.tokens_in, gen.tokens_out, gen.duration_ms

            sections = parse_article_output(text)
            scores = bm.score_all(kw, sections, spec)
            if opts["judge"] and not opts["dry"]:
                scores.update(bm.run_judge(ai_generate, sections.get("ARTICLE_HTML", "")))

            cost = pricing.estimate_text_cost(model, t_in, t_out)
            total_cost += cost
            record = {
                "niche": niche, "keyword": kw, "model": model,
                "tokens_in": t_in, "tokens_out": t_out, "cost_usd": round(cost, 6),
                "duration_ms": dur, "overall": bm.overall_score(scores),
                "scores": scores, "sections": sections,
            }
            results.append(record)
            with open(os.path.join(run_dir, f"{niche}_{slugify(kw)}.json"), "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            self.stdout.write(f"  [{niche:11}] {kw[:40]:40} overall={record['overall']:>5}  ${cost:.4f}")

        agg = bm.aggregate(results)
        meta = {
            "timestamp": ts, "prompt_version": PROMPT_VERSION, "model": opts["model"] or "default",
            "length": opts["length"], "judge": opts["judge"] and not opts["dry"],
        }
        report = bm.render_report(meta, results, agg)
        report_path = os.path.join(rep_dir, f"report-{ts}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Selesai {len(results)} artikel · total HPP ${total_cost:.4f}"))
        self.stdout.write("Terlemah: " + ", ".join(f"{d}={v}" for d, v in agg["ranked"][:3]))
        self.stdout.write(f"Report: {report_path}")
