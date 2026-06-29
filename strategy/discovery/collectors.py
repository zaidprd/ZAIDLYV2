"""Discovery collectors — extract keyword candidates from real data, no AI.

Active: Website, Sitemap, Category. The rest are placeholders returning [] so the
pipeline architecture is ready without changing code when they're implemented.
"""
import re
from urllib.parse import urlparse

from . import http
from .base import Collector, KeywordCandidate

_CATEGORY_HINTS = ('category', 'kategori', 'product-category', 'collections', '/c/', '/cat/')


def _clean(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _valid(phrase):
    return 2 <= len(phrase) <= 80 and re.search(r'[a-zA-Z]', phrase)


def _slug_to_phrase(slug):
    return re.sub(r'[-_]+', ' ', slug).strip()


def _last_segment(url_path):
    seg = [s for s in url_path.split('/') if s]
    return seg[-1] if seg else ''


class WebsiteCollector(Collector):
    name = 'website'

    def collect(self, project):
        url = http.normalize(project.website_url)
        if not url:
            return []
        html = http.fetch(url)
        if not html:
            return []
        out = []

        title = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
        if title:
            phrase = _clean(title.group(1))
            if _valid(phrase):
                out.append(KeywordCandidate(phrase, self.name, url, 0.7, 'title'))

        for h in re.findall(r'<h[1-3][^>]*>(.*?)</h[1-3]>', html, re.I | re.S):
            phrase = _clean(h)
            if _valid(phrase):
                out.append(KeywordCandidate(phrase, self.name, url, 0.6, 'heading'))

        meta = re.search(r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\'](.*?)["\']', html, re.I)
        if meta:
            for kw in meta.group(1).split(','):
                phrase = _clean(kw)
                if _valid(phrase):
                    out.append(KeywordCandidate(phrase, self.name, url, 0.8, 'meta-keywords'))
        return out


class SitemapCollector(Collector):
    name = 'sitemap'

    def collect(self, project):
        base = http.normalize(project.website_url)
        if not base:
            return []
        xml = http.fetch(base.rstrip('/') + '/sitemap.xml')
        if not xml:
            return []
        out = []
        for loc in re.findall(r'<loc>(.*?)</loc>', xml, re.I | re.S):
            loc = loc.strip()
            slug = _last_segment(urlparse(loc).path)
            if '.' in slug:  # skip files like image.jpg / page.xml
                continue
            phrase = _slug_to_phrase(slug)
            if _valid(phrase):
                out.append(KeywordCandidate(phrase, self.name, loc, 0.5, 'sitemap-slug'))
        return out


class CategoryCollector(Collector):
    name = 'category'

    def collect(self, project):
        url = http.normalize(project.website_url)
        if not url:
            return []
        html = http.fetch(url)
        if not html:
            return []
        out = []
        seen = set()
        for href in re.findall(r'href=["\'](.*?)["\']', html, re.I):
            low = href.lower()
            if not any(h in low for h in _CATEGORY_HINTS):
                continue
            slug = _last_segment(urlparse(href).path)
            phrase = _slug_to_phrase(slug)
            if _valid(phrase) and phrase.lower() not in seen:
                seen.add(phrase.lower())
                out.append(KeywordCandidate(phrase, self.name, href, 0.6, 'category-link'))
        return out


# Placeholders — architecture ready, return empty until implemented.
class BlogCollector(Collector):
    name = 'blog'

    def collect(self, project):
        return []


class CompetitorCollector(Collector):
    name = 'competitor'

    def collect(self, project):
        return []


class SERPCollector(Collector):
    name = 'serp'

    def collect(self, project):
        return []


class PAACollector(Collector):
    name = 'paa'

    def collect(self, project):
        return []


class RelatedCollector(Collector):
    name = 'related'

    def collect(self, project):
        return []
