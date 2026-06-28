# PRD — SEO.Zaidly: Mesin Artikel SEO

> Status: draft revisi-2 (2026-06-29). Dokumen acuan sebelum coding.

## 0. Sequencing — baca ini dulu

**Target pertama BUKAN membuat framework AI.** Target pertama = **generator artikel SEO terbaik di Indonesia** yang konsisten lolos Yoast, ramah Google AI Overview, auto-publish ke WordPress, auto-post ke Threads, murah operasional, dan **margin ≥50%**.

- **Fase A (MVP, sekarang):** bangun generator terbaik di **jalur LOKAL** (`ai_service` + prompt builder + quality gate). Tidak bergantung pada Hermes.
- **Fase B (setelah sukses & ada pelanggan):** generalisasi ke **Hermes Agent** (migrasi Tahap 0–3 yang sudah dirancang). **DITUNDA.**

Visi jangka panjang tetap "SEO.Zaidly mempekerjakan Hermes", tapi MVP dikerjakan lokal lebih dulu agar cepat menghasilkan & terbukti laku.

## 1. Visi & positioning

SEO.Zaidly **bukan AI writer**. Ia memproduksi **artikel SEO berkualitas tinggi**, bukan sekadar artikel hasil AI. **Aset utama produk = kualitas prompt + quality gate + workflow.** Di sinilah nilai jual dibanding AI writer biasa.

Arsitektur target (dicapai bertahap): **Django** = management layer (auth, dashboard, billing, project, WP site, queue, jadwal, riwayat, analytics) · **execution** = jalur Lokal sekarang, Hermes nanti · **LLM** = "otak" komoditas, ditukar via config.

## 2. Prinsip produk

1. **MVP-first, bukan framework-first** (lihat §0).
2. **Quality-first.** Output mengikuti praktik SEO terbaik (Yoast semampunya, rich snippet/schema, struktur ramah Search & AI Overview). Tanpa jaminan AI Overview — struktur dirancang untuk memaksimalkan peluang.
3. **Profit-aware.** Setiap fitur mempertimbangkan efisiensi biaya AI. Margin atas HPP: **min 50%, ideal 70–80%**.
4. **Config over code.** Provider, model, fallback, timeout, retry — semua konfigurasi, tanpa ubah business logic.
5. **Safe & measurable.** Tidak publish sebelum lolos quality gate; tiap generate mencatat model/token/biaya/durasi → HPP terhitung.

## 3. Prompt Builder (CORE PRODUCT)

Prompt **tidak boleh hardcode**. Harus ada **Prompt Builder**: prompt dirakit secara dinamis & komposabel dari parameter, **mudah di-improve tanpa banyak ubah kode** (template berversi / konfigurasi, bukan string menyebar di logic).

### 3.1 Parameter yang dirakit

| Parameter | Pilihan / format |
|---|---|
| Panjang artikel | 1000 / 1500 / 2000 / 3000 / 5000+ kata |
| Tone | formal, profesional, santai, edukatif, persuasif, dll |
| Writing style | blog, review, tutorial, listicle, evergreen, news |
| Target audience | teks bebas |
| Bahasa | id / en (extensible) |
| Keyword utama | 1 wajib |
| Secondary keyword | 0..n |
| LSI keyword | 0..n (semantik) |
| Brand voice | teks bebas / preset per project |
| CTA | teks / toggle |
| FAQ | toggle |
| Internal link | opsional, daftar URL |
| External link | opsional, daftar URL otoritatif |
| Schema | toggle / auto (Article + FAQPage) |
| Google AI Overview optimization | toggle (answer-first, entitas, struktur Q&A) |
| Yoast SEO optimization | toggle (aturan §5.1) |

### 3.2 Desain teknis Prompt Builder

- **Komposabel**: tiap parameter = fragmen prompt yang digabung builder → satu system prompt final.
- **Berversi**: `prompts/article_vN` atau template terdaftar → A/B & rollback.
- **Terisolasi dari business logic**: ubah kualitas prompt tanpa menyentuh views/tasks/engine.
- **Golden set + rubrik**: kumpulan keyword uji + skor (pakai SEO scorer §5) untuk mengukur konsistensi antar-run & antar-model. Target: "konsisten lolos gate ≥ X%", bukan "sekadar jadi".

### 3.3 Kerangka per writing style
blog: intro hook → 5–7 H2 → kesimpulan · listicle: intro → N item bernomor → ringkasan · tutorial: prasyarat → langkah berurutan → troubleshooting · review: verdict atas → fitur → pro/kontra → verdict akhir · evergreen: definisi → konteks → praktik → FAQ · news: inverted pyramid.

## 4. Output (artefak)

meta title (≤60 char, keyword) · meta description (≤155 char, keyword, ada CTA-baca) · SEO slug (kebab-case, fokus keyword) · artikel HTML (tag: h2,h3,p,ul,ol,li,strong,em,table; tanpa h1/html/body) · FAQ (3–5 Q&A bila aktif) · JSON-LD (Article + FAQPage bila relevan) · featured image (§6) · alt text gambar (deskriptif, sadar-keyword).

## 5. Quality Gate (WAJIB, dengan auto-revisi)

**Artikel TIDAK boleh langsung publish.** Harus lewat gate otomatis. Jika belum memenuhi standar → **revisi otomatis** (kirim ulang ke model dengan daftar kriteria yang gagal) → cek ulang → publish hanya bila lolos atau batas retry tercapai.

```
generate → SEO scorer → lolos? ──ya──→ siap publish
                          │
                          └─tidak→ auto-revise (≤ N retry) → scorer → …
                                   (gagal terus → tandai "perlu review manual")
```

### 5.1 Checklist gate
panjang ≥ target · keyword density (~0.5–2.5%, natural) · struktur heading (H2/H3 wajar) · meta title (≤60, keyword) · meta description (≤155, keyword) · slug valid · FAQ ada (bila diminta) · schema valid (bila diminta) · internal link ada (bila diminta) · external link ada (bila diminta) · image alt text ada · readability (paragraf/kalimat pendek, transition words) · **Yoast SEO score** ≥ ambang.

### 5.2 Implementasi
Kembangkan `generator/seo.py` (`validate`) menjadi **SEO scorer** ala-Yoast yang mengembalikan skor + daftar kegagalan terstruktur (dipakai untuk: gate, input auto-revisi, dan skor SEO yang ditampilkan ke user).

### 5.3 Guard biaya
Auto-revisi = panggilan AI tambahan → menambah HPP. **Batasi `N` retry** (config) dan catat biaya revisi ke telemetri (§8). Gagal lolos setelah `N` → status "perlu review manual", bukan loop tak terbatas.

## 6. Featured Image (WAJIB, otomatis)

```
Generate Prompt → Generate Image → Generate Alt Text → Upload ke WordPress → Set sebagai Featured Image
```

Detail: susun `image_prompt` (dari keyword/judul/style) → generate via image model (config; kosong = skip bila dinonaktifkan) → generate alt text sadar-keyword → upload `/wp/v2/media` (dapat `media_id`) → set alt text pada media → set `featured_media` saat publish. Sebagian sudah ada di `publisher`; PRD mewajibkan **alt text** & menjadikan image bagian resmi workflow.

## 7. Model Strategy (config, tidak hardcode)

Semua via konfigurasi, tanpa ubah business logic:

| Setelan | Fungsi |
|---|---|
| Default model | model paling **konsisten** untuk artikel SEO (ditentukan dari uji konsistensi) |
| Fallback model(s) | dipakai bila default gagal/timeout |
| Timeout | batas waktu per panggilan |
| Retry | jumlah percobaan ulang sebelum pindah fallback |

Tujuan utama: **konsistensi kualitas**, bukan sekadar murah. Pola `ai_service`/`AIProvider` yang ada sudah memberi swappability provider; tambahkan daftar fallback + timeout + retry di config.

## 8. Cost Tracking → HPP per artikel (WAJIB)

Tiap job menyimpan: `model_text` · `model_image` · `tokens_in` · `tokens_out` · `image_count` · `cost_text_usd` · `cost_image_usd` · `cost_total_usd` (HPP) · `duration_ms` · `retry_count` (biaya revisi) · `word_count_target` · `word_count_actual` · `credit_charged`.

Dari sini: HPP rata-rata per tier panjang, margin per paket harga, dasar harga kredit. Target margin **≥50% (ideal 70–80%)**. Catatan: HPP AI langsung belum termasuk fee Mayar.id, VPS, & rate gagal — layer-kan untuk margin bisnis riil. Lihat kalkulator HPP→harga.

## 9. Praktik SEO yang di-encode

**Yoast**: keyword utama hadir di meta title, meta description, slug, paragraf pertama (10% awal), ≥1 H2, dan alt text; densitas natural; readability (paragraf/kalimat pendek, transition words, distribusi subjudul, internal + outbound link, panjang memadai). Set meta ke field Yoast (`_yoast_wpseo_title/metadesc`) via REST — lihat open question §13.
**Rich snippet / AI Overview**: subjudul berbasis pertanyaan; jawaban langsung & ringkas di dekat atas; data terstruktur (FAQPage, Article); list & tabel; nada otoritatif; kelengkapan semantik (entitas & sub-topik). Tanpa jaminan.

## 10. Definition of Done — MVP

MVP dianggap selesai bila generator:
1. **Konsisten lolos Yoast SEO** (gate §5 lulus ≥ ambang, lintas run).
2. **Ramah Google AI Overview** (struktur §9 terpenuhi).
3. **Auto-publish ke WordPress** (+ Yoast meta + featured image & alt).
4. **Auto-post ke Threads**.
5. **Murah operasional** — HPP terukur per artikel.
6. **Margin bisnis ≥50%** pada konfigurasi default, harga wajar untuk pasar Indonesia.

## 11. Roadmap

**Fase A — MVP (sekarang, jalur lokal):**
A1. Prompt Builder (§3) + parameter lengkap.
A2. Quality Gate + auto-revisi (§5) lewat SEO scorer.
A3. Model Strategy: default + fallback + timeout + retry (§7).
A4. Featured Image pipeline + alt text (§6).
A5. Cost tracking / HPP (§8) + tampil di analytics.
A6. Auto-publish WP (Yoast meta) + auto-post Threads.
A7. Tetapkan harga kredit dari HPP (margin ≥50%).

**Fase B — Generalisasi Hermes (DITUNDA, setelah ada pelanggan):**
Tahap 0 spike → engine abstraction → HermesArticleEngine PoC → migrasi bertahap (Research→SEO→Image→Publish→Promotion). Detail tersimpan; tidak dikerjakan sampai Fase A sukses.

## 12. Scope

**In (Fase A):** prompt builder, generate judul+artikel (parameter §3), quality gate+auto-revisi, featured image+alt, publish WP (+Yoast meta), auto-post Threads, telemetri HPP, model fallback.
**Out (sekarang):** integrasi Hermes Agent (Fase B), jaminan ranking/AI Overview, multi-CMS selain WordPress, editor WYSIWYG penuh, internal-link otomatis dari crawl.

## 13. Open questions
1. **Meta ke Yoast**: field `_yoast_wpseo_*` via REST (butuh registrasi meta/plugin) vs RankMath vs UI manual?
2. **Sumber internal link**: sitemap WP otomatis vs input manual dulu?
3. **Schema**: inject JSON-LD ke konten vs andalkan Yoast?
4. **Default model & batas retry `N`**: tentukan dari uji konsistensi + guard biaya.
5. **Harga per tier panjang**: flat vs beda per tier (3000+/5000+ jauh lebih mahal di HPP)?
