"""Best-effort homepage text fetch for business analysis.

Reads the customer's own site. Never raises — returns '' on any failure so the
analyzer can still work from the business description alone.
"""
import re

import requests


def fetch_homepage(url, max_chars=6000, timeout=10):
    if not url:
        return ''
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        resp = requests.get(url, timeout=timeout,
                            headers={'User-Agent': 'SEOZaidlyBot/1.0'})
        resp.raise_for_status()
        html = resp.text
    except requests.RequestException:
        return ''
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars]
