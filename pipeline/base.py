"""Minimal pipeline runner. No registry, no DI container — just an ordered list.

A Step mutates the shared PipelineContext. Pipeline.run executes the steps in
order, skipping any whose `enabled()` returns False, and records per-step timing
on the context (so cost/HPP can later be attributed per stage).
"""
import time


class Step:
    """One SEO stage. Subclasses set `name` and implement `run`."""

    name = "step"

    def enabled(self, ctx) -> bool:
        return True

    def run(self, ctx) -> None:
        raise NotImplementedError


class Pipeline:
    def __init__(self, steps):
        self.steps = steps

    def run(self, ctx):
        for step in self.steps:
            if not step.enabled(ctx):
                ctx.steps_log.append({'step': step.name, 'skipped': True})
                continue
            start = time.monotonic()
            step.run(ctx)
            ctx.steps_log.append({'step': step.name, 'ms': int((time.monotonic() - start) * 1000)})
        return ctx
