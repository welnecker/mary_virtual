from __future__ import annotations

from typing import Iterable
import logging
import inspect
from time import perf_counter
import requests
from token_usage import classify_call, make_usage_event, record


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_LOG = logging.getLogger(__name__)


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
    call_type: str = "",
) -> str:
    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY não configurada.")
    if not model:
        raise OpenRouterError("Modelo não informado.")

    candidates: Iterable[str] = [model] + ([fallback_model] if fallback_model else [])
    last_error: Exception | None = None
    caller = inspect.currentframe().f_back
    stage = classify_call(caller.f_code.co_filename if caller else "", call_type=call_type)
    del caller

    for candidate in candidates:
        # Cada tentativa gera seu próprio evento, inclusive HTTP/JSON/choices vazios.
        for attempt in range(2):
            started = perf_counter()
            response = None
            data = {}
            request_status = "ERROR"
            error_code = ""
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
                    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
                    finish_reason = choices[0].get("finish_reason") if isinstance(choices[0], dict) else None
                    _LOG.warning(
                        "OPENROUTER_EMPTY_RESPONSE model=%s attempt=%s finish_reason=%s "
                        "completion_tokens=%s reasoning_tokens=%s",
                        candidate, attempt + 1, finish_reason,
                        usage.get("completion_tokens"),
                        (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
                        if isinstance(usage.get("completion_tokens_details"), dict) else None,
                    )
                    request_status = "EMPTY_RESPONSE"
                    last_error = OpenRouterError(
                        f"OpenRouter retornou resposta vazia (HTTP {response.status_code}, modelo {candidate})."
                    )
                    if attempt == 0:
                        continue
                    break
                request_status = "SUCCESS"
                return content.strip()
            except requests.HTTPError as exc:
                request_status = "HTTP_ERROR"
                error_code = "HTTP_ERROR"
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
                break
            except Exception as exc:
                error_code = type(exc).__name__
                last_error = exc
                break
            finally:
                record(make_usage_event(
                    model=candidate, call_type=stage, attempt=attempt + 1,
                    duration_ms=(perf_counter() - started) * 1000,
                    status=request_status,
                    http_status=getattr(response, "status_code", None),
                    request_messages=messages, response=data, error_code=error_code,
                ))

    raise OpenRouterError(f"Falha ao consultar OpenRouter: {last_error}")
