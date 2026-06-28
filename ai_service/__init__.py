"""AI Service — the single abstraction layer for all AI operations.

Usage from anywhere in the app:

    from ai_service import generate, generate_text, generate_image

    result = generate(messages)          # GenerationResult: text + cost telemetry
    text   = generate_text(messages)     # just the string
    url    = generate_image(prompt)

The concrete backend is chosen by the AI_PROVIDER env var (default:
"openai_compatible"). Application code must never import a provider directly,
so the backend can be swapped purely through configuration.

Model strategy (config-driven, no business-logic changes):
    AI_DEFAULT_MODEL    primary model (most consistent for SEO articles)
    AI_FALLBACK_MODELS  comma-separated models tried if the primary fails
    AI_TIMEOUT          per-call timeout in seconds
    AI_MAX_RETRIES      extra attempts per model before moving to the next
"""
from decouple import config

from ai_service.base import AIProvider, AIServiceError, GenerationResult

__all__ = [
    'generate', 'generate_text', 'generate_image', 'get_provider',
    'AIProvider', 'AIServiceError', 'GenerationResult',
]

_provider = None


def _build_provider() -> AIProvider:
    name = config('AI_PROVIDER', default='openai_compatible')
    if name == 'openai_compatible':
        from ai_service.providers.openai_compatible import OpenAICompatibleProvider
        return OpenAICompatibleProvider()
    raise AIServiceError(f"Unknown AI_PROVIDER: {name!r}")


def get_provider() -> AIProvider:
    """Return the configured provider (built once per process)."""
    global _provider
    if _provider is None:
        _provider = _build_provider()
    return _provider


def _model_chain(explicit=None):
    """Ordered list of models to try: [primary] + fallbacks (deduped)."""
    primary = explicit or config('AI_DEFAULT_MODEL', default='gpt-4o-mini')
    raw = config('AI_FALLBACK_MODELS', default='')
    fallbacks = [m.strip() for m in raw.split(',') if m.strip()]
    chain = [primary]
    for m in fallbacks:
        if m not in chain:
            chain.append(m)
    return chain


def generate(messages, *, model=None, temperature=0.7, max_tokens=4000) -> GenerationResult:
    """Generate text with automatic fallback + retry, returning telemetry.

    Tries each model in the chain; for each, retries up to AI_MAX_RETRIES extra
    times on failure (timeout/error) before moving to the next model. Raises
    AIServiceError only if every model fails.
    """
    provider = get_provider()
    timeout = config('AI_TIMEOUT', default=120, cast=int)
    max_retries = config('AI_MAX_RETRIES', default=1, cast=int)

    chain = _model_chain(model)
    attempts = 0
    last_error = None

    for idx, mdl in enumerate(chain):
        for _ in range(max_retries + 1):
            attempts += 1
            try:
                result = provider.complete(
                    messages, model=mdl, temperature=temperature, max_tokens=max_tokens, timeout=timeout
                )
                result.attempts = attempts
                result.fallback_used = idx > 0
                return result
            except AIServiceError as e:
                last_error = e

    raise AIServiceError(f"All models failed {chain} after {attempts} attempts: {last_error}")


def generate_text(messages, *, model=None, temperature=0.7, max_tokens=4000) -> str:
    """Convenience wrapper: return just the generated text."""
    return generate(messages, model=model, temperature=temperature, max_tokens=max_tokens).text


def generate_image(prompt, *, model=None, size="1024x1024") -> str:
    return get_provider().generate_image(prompt, model=model, size=size)
