import re


def validate(keyword, title, article_html, meta_description):
    kw = keyword.lower()
    html_lower = article_html.lower()
    checks = []

    def check(label, passed, tip=''):
        checks.append({'label': label, 'passed': passed, 'tip': tip})
        return passed

    check(
        'Keyword di judul',
        kw in title.lower(),
        'Masukkan keyword utama ke dalam judul artikel.',
    )

    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', article_html, re.IGNORECASE | re.DOTALL)
    h1_text = re.sub(r'<[^>]+>', '', h1_match.group(1)).lower() if h1_match else ''
    check('Keyword di H1', kw in h1_text, 'H1 harus mengandung keyword utama.')

    first_p = re.search(r'<p[^>]*>(.*?)</p>', article_html, re.IGNORECASE | re.DOTALL)
    first_p_text = re.sub(r'<[^>]+>', '', first_p.group(1)).lower() if first_p else ''
    check('Keyword di paragraf pertama', kw in first_p_text, 'Sebutkan keyword di paragraf pembuka.')

    check('Meta description ada', bool(meta_description), 'Tambahkan meta description.')
    check(
        'Panjang meta description',
        120 <= len(meta_description) <= 155 if meta_description else False,
        'Meta description idealnya 120-155 karakter.',
    )

    h2_count = len(re.findall(r'<h2', html_lower))
    check('Minimal 3 heading H2', h2_count >= 3, f'Hanya ada {h2_count} H2. Tambahkan lebih banyak sub-bagian.')

    plain_text = re.sub(r'<[^>]+>', ' ', article_html)
    word_count = len(plain_text.split())
    check('Panjang artikel ≥ 800 kata', word_count >= 800, f'Baru {word_count} kata. Target minimal 800.')

    check('Ada section FAQ', 'faq' in html_lower, 'Tambahkan bagian FAQ untuk SEO lebih baik.')

    passed = sum(1 for c in checks if c['passed'])
    score = round((passed / len(checks)) * 100)

    return {
        'score': score,
        'checks': checks,
        'word_count': word_count,
        'h2_count': h2_count,
    }
