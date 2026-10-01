from __future__ import annotations

from typing import Iterable
import requests


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterError(RuntimeError):
    pass


def chat(
    *,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.9,
    max_tokens: int = 700,
    fallback_model: str | None = None,
) -> str:
    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY não configurada.")
    if not model:
        raise OpenRouterError("Modelo não informado.")

    candidates: Iterable[str] = [model] + ([fallback_model] if fallback_model else [])
    last_error: Exception | None = None

    for candidate in candidates:
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/welnecker/mary_virtual",
                    "X-Title": "Mary Core 2",
                },
                json={
                    "model": candidate,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise OpenRouterError("O modelo retornou resposta vazia.")
            return text.strip()
        except Exception as exc:
            last_error = exc

    raise OpenRouterError(f"Falha ao consultar OpenRouter: {last_error}")
