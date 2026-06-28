"""Deprecated shim.

AI logic now lives in the provider-agnostic `ai_service` package. Import from
there instead:

    from ai_service import generate_text, generate_image

This module is kept only so older imports keep working.
"""
from ai_service import generate_image, generate_text  # noqa: F401


def call_ai(messages, model=None, temperature=0.7, max_tokens=4000):
    return generate_text(messages, model=model, temperature=temperature, max_tokens=max_tokens)
