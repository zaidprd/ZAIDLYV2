"""Provider for any OpenAI-compatible HTTP API.

Works unchanged with the SumoPod OpenAI endpoint, the official OpenAI API, or
any gateway that exposes `/chat/completions` and `/images/generations`.
Configured entirely from environment variables, so switching the backend URL
never requires a code change.

Performs a SINGLE call per `complete()`; fallback, retry and timeout policy
live in the service layer (`ai_service.generate`).
"""
import time

import requests
from decouple import config

from ai_service.base import AIProvider, AIServiceError, GenerationResult


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, api_key=None, base_url=None, default_model=None, image_model=None):
        self.api_key = api_key if api_key is not None else config('AI_API_KEY', default='')
        raw_base = base_url if base_url is not None else config('AI_BASE_URL', default='https://api.openai.com/v1')
        self.base_url = raw_base.rstrip('/')
        self.default_model = default_model if default_model is not None else config('AI_DEFAULT_MODEL', default='gpt-4o-mini')
        self.image_model = image_model if image_model is not None else config('AI_IMAGE_MODEL', default='')

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def complete(self, messages, *, model=None, temperature=0.7, max_tokens=4000, timeout=120):
        mdl = model or self.default_model
        start = time.monotonic()
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": mdl,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data['choices'][0]['message']['content'].strip()
            usage = data.get('usage') or {}
            return GenerationResult(
                text=text,
                model=mdl,
                tokens_in=int(usage.get('prompt_tokens', 0) or 0),
                tokens_out=int(usage.get('completion_tokens', 0) or 0),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            raise AIServiceError(str(e)) from e

    def generate_image(self, prompt, *, model=None, size="1024x1024"):
        model = model or self.image_model
        if not model:
            return ''
        try:
            resp = requests.post(
                f"{self.base_url}/images/generations",
                headers=self._headers(),
                json={"model": model, "prompt": prompt, "n": 1, "size": size},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()['data'][0].get('url', '')
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            raise AIServiceError(str(e)) from e
