def titles_prompt(keyword, language, tone, target_audience):
    lang = 'Bahasa Indonesia' if language == 'id' else 'English'
    audience = target_audience or 'pembaca umum'
    return [
        {
            "role": "system",
            "content": (
                f"Kamu adalah spesialis SEO. Buat 15 judul artikel SEO yang menarik.\n"
                f"Bahasa: {lang}. Tone: {tone}. Target pembaca: {audience}.\n"
                "Aturan:\n"
                "- Setiap judul harus mengandung keyword utama\n"
                "- Judul bervariasi: How-to, List, Ultimate Guide, Questions, dll\n"
                "- Panjang judul 40-70 karakter\n"
                "- Tulis HANYA daftar bernomor, tidak ada teks lain"
            ),
        },
        {
            "role": "user",
            "content": f"Keyword: {keyword}",
        },
    ]


def article_prompt(keyword, title, language, tone, target_audience):
    lang = 'Bahasa Indonesia' if language == 'id' else 'English'
    audience = target_audience or 'pembaca umum'
    return [
        {
            "role": "system",
            "content": (
                f"Kamu adalah penulis konten SEO profesional.\n"
                f"Bahasa: {lang}. Tone: {tone}. Target: {audience}.\n\n"
                "Format output:\n"
                "Baris pertama: META: [meta description 120-155 karakter]\n"
                "Baris kedua: SLUG: [slug-url-ramah-seo]\n"
                "Baris selanjutnya: artikel dalam format HTML.\n\n"
                "Struktur artikel:\n"
                "- <h1>: judul utama (mengandung keyword)\n"
                "- Paragraf intro 100-150 kata (keyword di kalimat pertama)\n"
                "- 5-7 bagian <h2> dengan konten bergizi\n"
                "- Gunakan <ul>/<ol> untuk poin-poin\n"
                "- Satu bagian FAQ dengan <h2>FAQ</h2> (3-5 pertanyaan dalam <h3>)\n"
                "- Kesimpulan singkat\n"
                "- Target minimal 800 kata\n"
                "- Hanya gunakan tag: h1, h2, h3, p, ul, ol, li, strong, em"
            ),
        },
        {
            "role": "user",
            "content": f"Keyword: {keyword}\nJudul: {title}\n\nTulis artikel lengkap sekarang.",
        },
    ]


def image_prompt(keyword, title):
    return (
        f"Professional blog featured image for article about '{keyword}'. "
        f"Clean, modern design. No text overlay. High quality photography style."
    )
