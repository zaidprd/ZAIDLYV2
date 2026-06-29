"""ImageStep — generate the featured image.

Best-effort: a failure here must never fail the whole article (the image is
uploaded + set as featured later, in the publish job). Skips silently when image
generation is unconfigured.
"""
from ..base import Step


class ImageStep(Step):
    name = "image"

    def run(self, ctx):
        job = ctx.job
        img_prompt = (ctx.sections.get('IMAGE_PROMPT') or job.title) if ctx.sections else job.title
        try:
            ctx.image_url = ctx.generate_image(img_prompt)
        except Exception:
            ctx.image_url = ''
