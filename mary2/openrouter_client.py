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
            try:
                data = response.json()
            except ValueError as exc:
                raise OpenRouterError(
                    f"OpenRouter retornou HTTP {response.status_code} com resposta não JSON."
                ) from exc
            if not isinstance(data, dict):
                raise OpenRouterError(
                    f"OpenRouter retornou formato inesperado (HTTP {response.status_code})."
                )
            choices = data.get("choices")
            if not isinstance(choices, list) or not choices:
                error = data.get("error")
                if isinstance(error, dict):
                    detail = str(error.get("message") or error.get("code") or "erro sem mensagem")
                else:
                    detail = str(error or data.get("message") or "campo choices ausente")
                raise OpenRouterError(
                    f"OpenRouter respondeu HTTP {response.status_code}, modelo {candidate}: {detail[:500]}"
                )
            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, list):
                content = "".join(
                    item.get("text", "") for item in content
                    if isinstance(item, dict) and isinstance(item.get("text"), str)
                )
            if not isinstance(content, str) or not content.strip():
                raise OpenRouterError(
                    f"OpenRouter retornou resposta vazia (HTTP {response.status_code}, modelo {candidate})."
                )
            return content.strip()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "desconhecido"
            try:
                error_data = exc.response.json() if exc.response is not None else {}
                error = error_data.get("error", {}) if isinstance(error_data, dict) else {}
                detail = error.get("message", "") if isinstance(error, dict) else str(error)
            except ValueError:
                detail = ""
            last_error = OpenRouterError(
                f"OpenRouter HTTP {status}, modelo {candidate}: {str(detail)[:500] or 'requisição rejeitada'}"
            )
        except Exception as exc:
            last_error = exc

    raise OpenRouterError(f"Falha ao consultar OpenRouter: {last_error}")
