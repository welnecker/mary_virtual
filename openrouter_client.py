from __future__ import annotations

from typing import Any

import requests

from config import OPENROUTER_URL, REQUEST_TIMEOUT_SECONDS


class OpenRouterError(RuntimeError):
    pass


def chamar_openrouter(
    *,
    messages: list[dict[str, Any]],
    model: str,
    api_key: str,
    temperature: float = 0.9,
    max_tokens: int = 500,
) -> str:
    if not api_key.strip():
        raise OpenRouterError("OPENROUTER_API_KEY não configurada.")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://streamlit.app",
        "X-Title": "Mary Virtual",
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise OpenRouterError(f"Falha de conexão com o OpenRouter: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text[:2000]
        raise OpenRouterError(
            f"OpenRouter retornou HTTP {response.status_code}: {detail}"
        )

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError("Resposta inesperada do OpenRouter.") from exc

    if isinstance(content, str):
        result = content.strip()
    elif isinstance(content, list):
        result = "".join(
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict)
        ).strip()
    else:
        result = str(content or "").strip()

    if not result:
        raise OpenRouterError("O modelo retornou uma resposta vazia.")

    return result

