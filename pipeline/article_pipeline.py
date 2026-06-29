"""The article pipeline — one explicit, ordered list of steps.

This is the single place that defines the SEO flow. Adding a stage later
(internal links, indexing, rank tracking) = write a Step and insert it here.
No auto-discovery, no config magic — explicit beats clever.
"""
from .base import Pipeline
from .steps import ResearchStep, TitleStep, ArticleStep, ValidateStep, ImageStep


def build_article_pipeline():
    return Pipeline([
        ResearchStep(),   # SERP -> ResearchSnapshot (+ ContentBrief)  [stub today]
        TitleStep(),      # bulk/auto title when none given
        ArticleStep(),    # spec + research-grounded prompt -> generate
        ValidateStep(),   # quality gate + auto-revision
        ImageStep(),      # featured image (best-effort)
    ])
