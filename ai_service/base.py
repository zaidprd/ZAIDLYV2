"""Provider-agnostic contract for all AI operations in SEO.Zaidly.

The application talks ONLY to the `AIProvider` interface, never to a concrete
backend. This lets the AI provider (SumoPod OpenAI API, a self-hosted gateway,
or any other) be swapped via configuration without changing application logic.

`complete()` is the core text primitive — it returns a `GenerationResult`
carrying the text plus the telemetry every article needs for HPP/cost tracking
(model used, tokens in/out, duration). `generate_text()` is a thin convenience
wrapper for callers that only want the string.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


class AIServiceError(Exception):
    """Raised when an AI provider fails to fulfil a request."""


@dataclass
class GenerationResult:
    """Result of a single text generation, with cost/telemetry metadata."""

    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0
    attempts: int = 1
    fallback_used: bool = False


class AIProvider(ABC):
    """Contract every AI provider must implement."""

    @abstractmethod
    def complete(self, messages, *, model=None, temperature=0.7, max_tokens=4000, timeout=120) -> GenerationResult:
        """Run one chat completion and return text + usage telemetry.

        `messages` is a list of {"role": ..., "content": ...} dicts.
        Performs a single call to `model` (no fallback/retry — that is the
        service layer's job). Raises AIServiceError on failure.
        """

    @abstractmethod
    def generate_image(self, prompt, *, model=None, size="1024x1024") -> str:
        """Return a URL to a generated image.

        Returns '' when image generation is disabled/unconfigured.
        Raises AIServiceError on failure.
        """

    def generate_text(self, messages, *, model=None, temperature=0.7, max_tokens=4000) -> str:
        """Convenience: return just the text of a completion."""
        return self.complete(
            messages, model=model, temperature=temperature, max_tokens=max_tokens
        ).text
