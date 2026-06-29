"""PipelineContext — the data that flows through the SEO pipeline.

Concrete and SEO-specific by design (not a generic bag): each field is a real
artifact a step produces or consumes. The AI callables are injected here so the
task layer owns provider wiring and tests can swap them in one place.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class PipelineContext:
    job: object                         # queue_manager.QueueJob
    generate: Callable                  # ai_service.generate (injected for testability)
    generate_image: Callable            # ai_service.generate_image

    # research
    snapshot: object = None             # research.ResearchSnapshot
    brief: object = None                # research.brief.ContentBrief

    # generation
    spec: object = None                 # generator.prompt_builder.ArticleSpec
    max_tokens: int = 4000
    output_text: str = ""
    sections: dict = field(default_factory=dict)
    seo: dict = field(default_factory=dict)
    image_url: str = ""

    # accumulated telemetry (persisted to the job by the task layer)
    model_used: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0
    fallback_used: bool = False
    revision_count: int = 0

    steps_log: list = field(default_factory=list)  # per-step timing for HPP-by-stage

    def add_usage(self, gen):
        """Accumulate telemetry from an ai_service GenerationResult."""
        if self.model_used == "":
            self.model_used = gen.model
        self.tokens_in += gen.tokens_in
        self.tokens_out += gen.tokens_out
        self.duration_ms += gen.duration_ms
        self.fallback_used = self.fallback_used or gen.fallback_used
