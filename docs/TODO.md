# TODO / Status — SEO.Zaidly

> Lanjut di chat baru: **"Lanjut dari commit terakhir. Baca docs/TODO.md dan docs/PRD.md, lanjutkan langkah berikutnya."**
> Semua progres aman di GitHub `zaidprd/ZAIDLYV2` branch `main`. HEAD terakhir: **`d94be0b`**. Full test: **60 hijau**.

## Identitas produk (jangan berubah)
SEO.Zaidly = **SEO Operating System**, bukan AI Writer. User memberi **bisnis** (website/deskripsi/niche/goal/negara), sistem yang memutuskan keyword. Objek utama = **Campaign**. Artikel = output.
Aturan kunci: **AI hanya menganalisis** (cluster/intent/business value/judul) — TIDAK mengarang volume/difficulty/CPC (NULL kalau tak ada data). Keyword dari **data nyata** (website/sitemap/category; DataForSEO menyusul). **Satu queue** = django_q (cluster `hermes`); jangan tambah Celery/Redis. Reuse generator/QualityGate/Publisher/Research; jangan refactor besar.

## ✅ SELESAI

**Fase A — Article Engine (jalur lokal)**
Foundation (`ai_service`: model strategy + telemetry + `pricing.py`) · Project (Business Profile fields) · Prompt Builder (`generator/prompt_builder.py`, sentinel output) · Generate Judul · Generate Artikel (telemetri HPP) · Quality Gate + auto-revisi (`generator/seo.py`) · Featured Image (alt + Yoast meta) · Publish WP (+JSON-LD schema) · Threads · Billing (kredit flat + analytics HPP).

**SEO Strategy Engine (app `strategy/`) — Engine Batch 1–6**
- B1 Business Analyzer (`analyzer.py`) → `BusinessAnalysis`
- B2 Discovery Pipeline (`discovery/`) → `DiscoveredKeyword` (collectors Website/Sitemap/Category; Blog/Competitor/SERP/PAA/Related = placeholder kosong)
- B3 Keyword Intelligence (`intelligence.py`) → `TopicCluster` + cluster/intent/business_value/priority (null-safe)
- B4 Content Planner (`planner.py`) → `ContentPlanItem` (judul+scoring, reuse generator titles)
- B5 Campaign (`campaign.py`) → `Campaign`; mode **AI** + **Manual**, satu generator
- B6 Execution (`execution.py`) → drip per item via `run_generate_article` (reuse), status/progress

**Infra hardening I1–I5 (semua via django_q, no new system)**
- I1 `a702624` Campaign build **async** (`start_ai_campaign`→`strategy.tasks.run_build_ai_campaign`); `Campaign.progress_step`: analyzing→discovering→planning→completed
- I2 `52606cd` Discovery **cache** (`discover_keywords(refresh=False)`)
- I3 `df3bb86` ContentBrief **cache** (`research.service.get_or_create_brief`); brief masuk generate via `options` (no prompt rewrite)
- I4 `93b1848` **Scheduler** django_q `Schedule` (DAILY → `strategy.tasks.tick_campaign`), dihapus saat campaign completed
- I5 `d94be0b` `KeywordDataProvider` slot (`keyword_data.py`) — `NullProvider` default (metric NULL), `dataforseo`=NotImplemented; `enrich_keywords` di-hook ke campaign build (no-op hari ini)

## 🚧 BELUM / LANGKAH BERIKUT (engine dulu, deploy nanti)

1. **Wire ContentBrief lebih dalam ke prompt artikel** — sekarang brief baru kirim `secondary_keywords`/`entities` lewat options; tingkatkan agar PromptBuilder menulis dari brief (intent, headings, PAA, content gap). ← kandidat utama, paling berdampak ke ranking.
2. **SEO scoring berbasis brief** — entity/intent/topical coverage terhadap ContentBrief.
3. **Trigger/UI** — `start_ai_campaign` & `start_campaign` belum dipanggil dari mana pun (butuh view/UI). DITUNDA (user: belum buat UI).
4. **Deploy ke VPS SumoPod** — DITUNDA sampai engine stabil. PostgreSQL Managed DB (buat saat deploy → `.env`), django_q ORM broker, credential di `.env`. Checklist deploy ada di riwayat chat.
5. Lain-lain tertunda: Mayar.id top-up, Threads OAuth, Yoast penuh, tier pricing, DataForSEO nyata, Fase B Hermes Agent.

## JANGAN dikerjakan (sudah diputuskan)
SocialProvider / EmailProvider / StorageProvider / UI baru / refactor besar / queue kedua / mengarang metric SEO. "Kalau belum dipakai customer, jangan dibuat."

## Peta file kunci
- `strategy/` — SEO Strategy Engine (analyzer, discovery, intelligence, planner, campaign, execution, keyword_data, tasks). Model di `strategy/models.py`.
- `research/` — ContentBrief + cache (`service.get_or_create_brief`).
- `generator/` — article engine (prompt_builder, seo, tasks, parsing) — **reuse, jangan ubah arsitektur**.
- `ai_service/` — AI provider + pricing. `publisher/` — WP + Threads. `billing/` — kredit + HPP.
- `docs/PRD.md` — spesifikasi.

## CLI tes (tanpa UI)
```
python manage.py analyze_business <project_id>
python manage.py research_keyword "<keyword>"
python manage.py run_campaign_tick <campaign_id>
```

## Cara kerja
Commit kecil per batch → `python manage.py test` (harus hijau) → `git push origin main` → lanjut. Token menipis: commit dulu, baru berhenti.
