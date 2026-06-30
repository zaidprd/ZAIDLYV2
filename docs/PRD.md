# MASTER PRD — SEO.ZAIDLY

**AI SEO Operating System · Version 1.0**

> **CATATAN UNTUK AI:** PRD ini menggantikan SELURUH instruksi lama (termasuk draft revisi-2). Jika instruksi mana pun bertentangan dengan PRD ini, **PRD ini yang berlaku.**

---

## 1. Visi produk

SEO.ZAIDLY **BUKAN** AI Writer.
SEO.ZAIDLY adalah **AI SEO Operating System**.

Tujuan utamanya bukan membuat artikel.
Tujuan utamanya adalah **membantu website ranking di Google secara otomatis**.

Semua fitur wajib menjawab satu pertanyaan:

> *"Apakah fitur ini membantu website ranking?"*

Kalau jawabannya tidak, fitur tersebut tidak boleh dibuat.

## 2. Target user

Bukan content writer. Target: agency SEO, freelancer SEO, digital marketing, pemilik bisnis, blogger, perusahaan.
**Mereka tidak mau menulis. Mereka hanya mau ranking.**

## 3. Filosofi produk

User tidak boleh dipaksa menjadi SEO expert. User cukup mengisi: website, deskripsi bisnis, negara target. Lalu sistem mengurus sisanya.

Contoh — User: *"Saya jual panel listrik."* Sistem: ✓ Analisa website · ✓ Cari keyword · ✓ Kelompokkan keyword · ✓ Tentukan prioritas · ✓ Buat judul · ✓ Buat artikel · ✓ Publish — semua otomatis.

## 4. User flow

**AI Mode:** Business Profile → Business Analysis → Keyword Discovery → Keyword Intelligence → Content Planner → Campaign → Generate → Quality Gate → Publish → **Repeat every day**.

**Manual Mode:** tetap tersedia. User bisa paste keyword atau upload CSV untuk yang sudah punya research sendiri.

**Manual Mode dan AI Mode memakai generator artikel yang SAMA. Tidak boleh ada generator kedua.**

## 5. Business profile

User hanya mengisi: Website URL, Business Description, Niche, Country, Goal, Language, Brand Voice, Target Audience. **Semua keputusan SEO berasal dari sini.**

## 6. Business Analyzer

Memahami bisnis. Input: website, description, homepage. Output: summary, offerings, themes, target audience, competitor hints. **Tidak boleh mengarang data SEO.**

## 7. Discovery Engine

Discovery berasal dari **data nyata**. Pipeline: Website → Sitemap → Category → Product → Blog → Competitor → SERP → People Also Ask → Related Searches.

Semua collector berdiri sendiri. Kalau belum tersedia → return kosong. Tidak boleh error.

## 8. AI TIDAK BOLEH MENGARANG

AI hanya boleh: ✓ Cluster · ✓ Intent · ✓ Business Value · ✓ Prioritas · ✓ Pilih keyword · ✓ Analisa.

AI **TIDAK BOLEH** membuat: ❌ Search Volume · ❌ Keyword Difficulty · ❌ CPC.

Jika tidak ada provider, nilai harus **`None`** — bukan angka palsu.

## 9. Keyword model

`KeywordCandidate` harus kaya. Minimal:

```
keyword, source, page_source, intent, business_value, priority_score,
cluster, parent_topic, confidence, notes, volume=None, difficulty=None, cpc=None
```

DataForSEO nanti tinggal mengisi kolom kosong.

## 10. Keyword Provider

Semua memakai provider: `KeywordDiscoveryProvider`. Implementasi: MockProvider, DataForSEOProvider, SerperProvider. **Tidak boleh ada kode yang tergantung provider tertentu.**

## 11. Keyword Intelligence

Setelah discovery, AI hanya menganalisa. Output: Cluster, Intent, Business Value, Priority, Recommended. **Tidak membuat keyword baru.**

## 12. Content Planner

Keyword → generate beberapa judul → diberi skor → dipilih terbaik. Hasil akhir: `ContentPlanItem`.

## 13. Campaign

**Objek utama sistem. Bukan QueueJob.**

Campaign berisi: Business, Keyword, Plan, Progress, Cost, ROI. Dua mode: AI Campaign, Manual Campaign.

## 14. Execution

Campaign menghasilkan `QueueJob`. **QueueJob hanyalah executor, bukan objek utama.**

## 15. Article generator

Tetap reuse. **Tidak boleh bikin generator baru.** Reuse: Prompt Builder, Quality Gate, AI Service, Publisher, Billing, `run_generate_article()`. Semua mode memakai generator yang sama.

## 16. Quality Gate

Artikel WAJIB lolos: SEO, Readability, Heading, FAQ, CTA, AI Overview, EEAT, Human Score, Semantic Coverage. Jika gagal → otomatis revisi.

## 17. Prompt Builder

Prompt Builder Premium berisi: EEAT, Semantic SEO, Anti AI cliché, Heading Discipline, Yoast, AI Overview, Human Writing. **Tidak boleh prompt pendek.**

## 18. Research

Research adalah aset. Disimpan ke database. **Bukan sekali pakai.** Yang disimpan: SERP, PAA, Related, Entities, Competitor, Schema, Internal Link, External Link, Meta, Brief.

## 19. Bulk mode

Dua mode.

**Mode 1 — AI Campaign:** user isi website, deskripsi, niche → sistem buat semua keyword → semua judul → campaign.

**Mode 2 — Manual Import:** paste keyword atau upload CSV. Format kolom: Keyword, Judul, Slug, Schedule, Kategori, Tag — semua opsional. Jika judul kosong, AI yang buat. Jika slug kosong, AI yang buat.

## 20. Billing

Semua memakai Credit. **1 artikel = 1 kredit.** Ada Top Up, History, Margin, Cost, HPP. Payment provider: Mock, Mayar.

## 21. Publisher

Support: WordPress, Threads, Auto Publish, Manual Publish, Scheduler, Featured Image, Schema, Yoast.

## 22. Scheduler

**Drip.** Misal: 3 artikel/hari. Campaign menghasilkan QueueJob setiap hari, bukan semua sekaligus.

## 23. Infrastruktur

- **Hosting:** VPS SumoPod
- **Domain:** `app.zaidly.com` (SEO tool lama tetap di `seo.zaidly.com`)
- **Queue:** django-q (Hermes). **Tidak boleh Celery.**
- **Database:** Managed PostgreSQL
- **Object Storage:** SumoPod Object Storage (jika nanti dibutuhkan)
- **Email:** SumoPod SMTP
- **Social:** Social Provider, Threads Provider

## 24. Hermes

Hermes adalah **worker**, bukan AI. **Tidak boleh muncul di UI.** Customer tidak perlu tahu Hermes.

## 25. AI Service

Provider abstraction. Support: Mock, OpenAI Compatible, SumoPod, Gemini, Claude. Fallback otomatis. Retry otomatis. Telemetry. Cost.

## 26. Roadmap Engine

- Batch 1 — Business Analyzer ✅
- Batch 2 — Discovery Pipeline ✅
- Batch 3 — Keyword Intelligence ✅
- Batch 4 — Content Planner ✅
- Batch 5 — Campaign ✅
- Batch 6 — Execution Queue ✅

## 27. Roadmap berikutnya

Campaign UI, Dashboard, Keyword Review, Plan Review, Coverage Score, SERP Coverage, DataForSEO, Storage, Email, Deploy.

## 28. Kode

Wajib: SOLID, Provider Pattern, Dependency Injection sederhana, commit kecil, test sebelum commit. **Tidak boleh over-engineering.**

## 29. Rules

AI **tidak boleh** membuat data SEO palsu. Semua angka SEO berasal dari provider nyata. Jika provider belum tersedia: **`None`** — bukan tebakan.

## 30. Deploy

Deploy ke VPS SumoPod: Gunicorn, Nginx, django-q, Managed PostgreSQL, Cloudflare.

Domain: `app.zaidly.com`. SEO tool lama (`seo.zaidly.com`) tetap berjalan.

## 31. Goal akhir

User cukup melakukan:

```
Isi Website  →  Klik Generate Campaign  →  Approve  →  Start
                                                       ↓
                                         Sistem bekerja setiap hari
                                                       ↓
                                              Website ranking
```

User **tidak perlu**: ❌ mencari keyword · ❌ membuat judul · ❌ membuat outline · ❌ menulis artikel · ❌ upload WordPress manual.

**SEO.ZAIDLY melakukan semuanya.**
