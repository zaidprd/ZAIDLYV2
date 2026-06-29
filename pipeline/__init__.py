"""SEO pipeline — the product's core engine.

A keyword flows through ordered Steps (research -> title -> article -> validate
-> image), accumulating data in a PipelineContext. This is deliberately a small,
SEO-specific orchestration, NOT a generic framework: steps are an explicit list,
there is no plugin registry or DI container, and provider seams exist only where
a real external backend can be swapped (AI, SERP, CMS).
"""
from .base import Pipeline, Step
from .context import PipelineContext
from .article_pipeline import build_article_pipeline

__all__ = ['Pipeline', 'Step', 'PipelineContext', 'build_article_pipeline']
