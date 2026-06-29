"""Business analysis prompt. The AI ANALYSES — it must not fabricate SEO data."""

LANG_NAMES = {"id": "Bahasa Indonesia", "en": "English"}


def build_intelligence_messages(business_context, keywords):
    """Ask the model to ANALYSE keywords (cluster + intent + business value).
    It must NOT invent volume/CPC/difficulty — those are not requested."""
    kw_list = "\n".join(f"- {k}" for k in keywords)
    system = (
        "Kamu adalah SEO strategist. ANALISIS daftar keyword di bawah untuk sebuah bisnis. "
        "Tugasmu HANYA menganalisis — JANGAN mengarang angka volume pencarian, CPC, atau difficulty.\n\n"
        "Untuk SETIAP keyword, tentukan:\n"
        "- cluster: nama topic cluster yang ringkas (kelompokkan keyword sejenis)\n"
        "- intent: salah satu dari informational/commercial/transactional/navigational\n"
        "- business_value: integer 0-100, seberapa relevan & bernilai bagi bisnis ini\n\n"
        "Keluarkan HANYA satu objek JSON valid (tanpa code fence):\n"
        '{"keywords":[{"keyword":"...","cluster":"...","intent":"...","business_value":0}]}'
    )
    user = f"Konteks bisnis:\n{business_context}\n\nKeyword:\n{kw_list}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_analysis_messages(profile, page_text=""):
    lang = LANG_NAMES.get(profile.get("language", "id"), profile.get("language", "id"))
    system = (
        "Kamu adalah SEO strategist. Tugasmu MENGANALISIS sebuah bisnis untuk menyiapkan "
        "riset SEO — BUKAN menulis artikel, BUKAN mengarang data.\n"
        "ATURAN KERAS: JANGAN membuat angka apa pun (volume pencarian, traffic, difficulty, CPC). "
        "Hanya simpulkan dari informasi yang diberikan.\n\n"
        f"Hasil dalam {lang}. Keluarkan HANYA satu objek JSON valid (tanpa code fence) dengan kunci:\n"
        "- summary: ringkasan bisnis 2-3 kalimat\n"
        "- offerings: array produk/jasa nyata yang ditawarkan (string)\n"
        "- themes: array tema/topik konten SEO yang relevan dengan bisnis ini "
        "(seed untuk discovery keyword; turunkan dari produk/jasa & audiens, bukan dikarang)\n"
        "- target_audience: deskripsi singkat audiens\n"
        "- competitor_hints: array jenis atau nama kompetitor yang mungkin (string)\n"
    )
    parts = [
        f"Nama bisnis: {profile.get('name', '')}",
        f"Website: {profile.get('website_url', '') or '(belum ada)'}",
        f"Deskripsi bisnis: {profile.get('business_description', '') or '(tidak diisi)'}",
        f"Niche: {profile.get('niche', '') or '(tidak diisi)'}",
        f"Target negara: {profile.get('target_country', '')}",
        f"Tujuan: {profile.get('goal', '')}",
        f"Target audiens (jika ada): {profile.get('target_audience', '') or '-'}",
    ]
    if page_text:
        parts.append(f"\nCuplikan isi homepage (data nyata dari website):\n{page_text}")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(parts)},
    ]
