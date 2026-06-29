"""ResearchStep — capture SERP findings and derive a ContentBrief.

STUB for now: it persists a ResearchSnapshot (so the knowledge-base wiring is in
place from day one) and produces an empty/stub ContentBrief. The real Serper.dev
provider drops in here later WITHOUT changing the pipeline or the prompt: it just
fills the snapshot + brief with real SERP data.
"""
from ..base import Step


class ResearchStep(Step):
    name = "research"

    def run(self, ctx):
        from research.models import ResearchSnapshot
        from research.brief import ContentBrief

        job = ctx.job
        project = job.project

        snapshot = ResearchSnapshot.objects.create(
            user=job.user,
            project=project,
            keyword=job.keyword,
            language=getattr(project, 'language', 'id'),
            provider='stub',
        )
        # Stub brief: carries no SERP signal yet, so build_article_messages keeps
        # its classic behaviour until a real provider is wired in.
        brief = ContentBrief(
            keyword=job.keyword,
            language=getattr(project, 'language', 'id'),
            snapshot_id=snapshot.pk,
        )
        snapshot.brief = brief.to_dict()
        snapshot.save(update_fields=['brief'])

        ctx.snapshot = snapshot
        ctx.brief = brief
