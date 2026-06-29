"""Tiny HTTP fetch for collectors. Returns '' on any failure (never raises)."""
import requests


def fetch(url, timeout=10):
    try:
        resp = requests.get(url, timeout=timeout, headers={'User-Agent': 'SEOZaidlyBot/1.0'})
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
        return ''


def normalize(url):
    if not url:
        return ''
    return url if url.startswith(('http://', 'https://')) else 'https://' + url
