"""Unit tests for the pipeline runner: order, enabled-skip, and per-step logging."""
from types import SimpleNamespace

from django.test import SimpleTestCase

from pipeline.base import Pipeline, Step


class RecordStep(Step):
    def __init__(self, name, on):
        self.name = name
        self.on = on

    def run(self, ctx):
        ctx.order.append(self.name)


class SkippableStep(Step):
    name = "skip"

    def enabled(self, ctx):
        return False

    def run(self, ctx):
        ctx.order.append("skip")  # must never run


class PipelineRunnerTests(SimpleTestCase):
    def _ctx(self):
        return SimpleNamespace(order=[], steps_log=[])

    def test_runs_in_order(self):
        ctx = self._ctx()
        Pipeline([RecordStep("a", True), RecordStep("b", True)]).run(ctx)
        self.assertEqual(ctx.order, ["a", "b"])
        self.assertEqual([s["step"] for s in ctx.steps_log], ["a", "b"])
        self.assertTrue(all("ms" in s for s in ctx.steps_log))

    def test_disabled_step_is_skipped(self):
        ctx = self._ctx()
        Pipeline([RecordStep("a", True), SkippableStep(), RecordStep("c", True)]).run(ctx)
        self.assertEqual(ctx.order, ["a", "c"])               # skip never ran
        self.assertEqual(ctx.steps_log[1], {"step": "skip", "skipped": True})
