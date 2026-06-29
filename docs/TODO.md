# TODO / Status — SEO.Zaidly (Fase A MVP)

> Cara lanjut di chat baru: **"Lanjut dari commit terakhir. Baca docs/TODO.md dan docs/PRD.md, lanjutkan langkah berikutnya."**
> Semua progres aman di GitHub: `zaidprd/ZAIDLYV2` branch `main`.

## ✅ Selesai (Fase A — jalur LOKAL, sudah di `main`, 21 test hijau)

- **Foundation** — `ai_service`: model strategy (default + fallback + timeout + retry), telemetry token (`GenerationResult`), `pricing.py` (estimator HPP).
- **Dashboard** — terverifikasi jalan.
- **Project** — field default Prompt Builder (writing style, length, brand voice, CTA).
- **Prompt Builder** (`generator/prompt_builder.py`) — komposabel & berversi; Yoast + AI Overview rules; guardrail anti-mengarang link/slug; kontrak output sentinel.
- **Generate Judul** — pakai Prompt Builder.
- **Generate Artikel SEO** — spec → builder → parse sentinel → telemetri HPP; opsi per-generate (panjang, style, secondary keyword, FAQ).
- **Quality Gate** (`generator/seo.py`) — SEO scorer lengkap + loop auto-revisi (cap retry, guard biaya); auto-publish digerbang skor.
- **Featured Image** — alt text di media WP + Yoast meta title.
- **Publish WordPress** — featured image + Yoast meta + inject JSON-LD schema.
- **Threads** — post otomatis pasca-publish (2-step Graph API).
- **Billing** — charge kredit flat (1 kredit/artikel) + analytics HPP di halaman kredit.
- PRD v2 (`docs/PRD.md`).

## 🚧 Belum / langkah berikut (prioritas atas → bawah)

1. **Validasi nyata** — isi `.env` (API key SumoPod), jalankan 1 generate sungguhan → cek kualitas artikel + HPP riil di halaman `/credits/`. (Semua verifikasi sejauh ini pakai test offline/mock, belum panggilan AI nyata.)
2. **Tuning prompt** — iterasi `generator/prompt_builder.py` berbasis hasil nyata (ini nilai jual produk).
3. **Pricing riil** — ganti tarif di `ai_service/pricing.py` ke tarif SumoPod; tetapkan harga jual kredit (target margin ≥50%, ideal 70-80%).
4. **Mayar.id top-up + webhook** — monetisasi (top-up kredit). DITUNDA, blocker jual.
5. **Threads OAuth** — sekarang token diisi manual via admin.
6. **Yoast penuh** — sekarang basic via meta REST tanpa plugin.
7. **Internal link otomatis** dari sitemap WP — sekarang manual.
8. **Tier pricing** per panjang artikel — sekarang flat.
9. **Fase B: Hermes Agent** — generalisasi ke execution engine Hermes (SumoPod) SETELAH produk sukses & ada pelanggan. Rancangan migrasi (Tahap 0-3) tersimpan; jangan dikerjakan dulu.

## Peta file kunci

- `ai_service/` — abstraksi AI (provider, strategy, pricing). Otak swappable via `.env`.
- `generator/prompt_builder.py` — **aset utama**, prompt SEO.
- `generator/seo.py` — quality gate / SEO scorer.
- `generator/tasks.py` — orkestrasi generate (builder → gate → revisi → telemetri).
- `generator/parsing.py` — parser output sentinel.
- `publisher/wordpress.py`, `publisher/tasks.py`, `publisher/threads.py` — publish WP + Threads.
- `billing/analytics.py` — HPP/biaya.
- `docs/PRD.md` — spesifikasi lengkap.

## Cara kerja commit
Commit per fitur besar (atau maksimal tiap 1-2 jam) lalu `git push origin main`, supaya progres aman kalau sesi habis.
