from __future__ import annotations

"""OpenRouter chat adapter with bounded recovery for reasoning-heavy models.

Keep the proven Gemini 3 Flash behavior intact. Other models receive a
stage-aware output budget; an empty reasoning-only completion is retried with
a *different* budget/effort, never with the same exhausted configuration.
"""

from typing import Iterable
import inspect
import logging
from time import perf_counter

import requests

from token_usage import classify_call, make_usage_event, record


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_LOG = logging.getLogger(__name__)

# These are conservative pilot budgets, not guarantees or required spending.
# Never reduce a caller's explicitly larger max_tokens.
_COMPAT_MIN_TOKENS = {
    "SEMANTIC_DIRECTOR": 4500,
    "CONVERSATION_STATE": 1100,
    "REDACTOR": 2000,
    "INPUT_ROUTER": 900,
    "USER_UNDERSTANDING": 1300,
    "EMOTION_CLASSIFIER": 900,
}
_REASONING_FAMILIES = ("deepseek/", "xiaomi/", "z-ai/", "qwen/", "moonshotai/", "openai/", "anthropic/")
_MAX_RECOVERY_TOKENS = 9000


class OpenRouterError(RuntimeError):
    pass


def _deepseek_v41_flash(model: str) -> bool:
    """The V4.1 Flash family exposes thinking controls, but not 'minimal'."""
    return model.lower().startswith("deepseek/deepseek-v4.1-flash")


def _mimo_v26_pro(model: str) -> bool:
    return model.lower() == "xiaomi/mimo-v2.6-pro"


def _preserve_gemini(model: str) -> bool:
    # Only Gemini uses the unchanged baseline. Gemma is a separate family.
    return model.lower().startswith("google/gemini-")


def _request_config(model: str, stage: str, requested_tokens: int, *, recovery: bool) -> dict:
    tokens = max(1, int(requested_tokens))
    if _preserve_gemini(model):
        return {"max_tokens": tokens}

    if _mimo_v26_pro(model):
        # Keep an explicitly higher caller budget and the semantic director's
        # minimum; this pilot changes reasoning only for MiMo-V2.6-Pro.
        tokens = max(tokens, _COMPAT_MIN_TOKENS.get(stage, 1400), 3500 if recovery else 3000)
        return {
            "max_tokens": tokens,
            "reasoning": {"max_tokens": 768} if recovery else {"enabled": False},
        }

    tokens = max(tokens, _COMPAT_MIN_TOKENS.get(stage, 1400))
    if recovery and not _deepseek_v41_flash(model):
        tokens = min(_MAX_RECOVERY_TOKENS, max(tokens + 1200, int(tokens * 1.65)))
    config = {"max_tokens": tokens}
    if _deepseek_v41_flash(model):
        # This workload needs *visible* speech/JSON, not a long private trace.
        # Disable thinking first; if the provider ignores that, retry with an
        # explicit, small reasoning budget rather than 7,425+ output tokens.
        config["reasoning"] = {"max_tokens": 768} if recovery else {"enabled": False}
        if recovery:
            config["max_tokens"] = max(tokens, 2600)
    elif model.lower().startswith(_REASONING_FAMILIES):
        # Effort is a gateway hint; some upstream providers ignore it.
        config["reasoning"] = {"effort": "minimal" if recovery else "low"}
    return config


def _visible_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts).strip()
    return ""


def _reasoning_exhausted(choice: dict, data: dict, budget: int) -> bool:
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    details = usage.get("completion_tokens_details")
    details = details if isinstance(details, dict) else {}
    try:
        output = int(usage.get("completion_tokens") or 0)
        reasoning = int(details.get("reasoning_tokens") or 0)
    except (TypeError, ValueError):
        return False
    # A provider can report a few extra tokens. Require a positive signal of
    # thinking plus a near-zero visible answer; do not classify generic errors.
    return (
        choice.get("finish_reason") == "length"
        and reasoning > 0
        and output >= max(1, budget - 16)
        and output - reasoning <= 32
    )


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

    candidates: Iterable[str] = [model] + (
        [fallback_model] if fallback_model and fallback_model != model else []
    )
    last_error: Exception | None = None
    caller = inspect.currentframe().f_back
    stage = classify_call(caller.f_code.co_filename if caller else "", call_type=call_type)
    del caller

    for candidate in candidates:
        # Keep at most two billed attempts per candidate.
        recovery = False
        remove_reasoning = False
        for attempt in range(2):
            started = perf_counter()
            response = None
            data: dict = {}
            request_status = "ERROR"
            error_code = ""
            config = _request_config(candidate, stage, max_tokens, recovery=recovery)
            if remove_reasoning:
                config.pop("reasoning", None)
            payload = {
                "model": candidate,
                "messages": messages,
                "temperature": temperature,
                **config,
            }
            if _mimo_v26_pro(candidate):
                # Prefer the faster MiMo endpoint while retaining OpenRouter's
                # provider failover if PrimaLabs is temporarily unavailable.
                payload["provider"] = {
                    "order": ["primalabs"],
                    "allow_fallbacks": True,
                }
            try:
                response = requests.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/welnecker/mary_virtual",
                        "X-Title": "Mary Core 2",
                    },
                    json=payload,
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
                    detail = (
                        str(error.get("message") or error.get("code") or "erro sem mensagem")
                        if isinstance(error, dict)
                        else str(error or data.get("message") or "campo choices ausente")
                    )
                    raise OpenRouterError(
                        f"OpenRouter respondeu HTTP {response.status_code}, modelo {candidate}: {detail[:500]}"
                    )
                choice = choices[0] if isinstance(choices[0], dict) else {}
                message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
                content = _visible_text(message)
                if content:
                    request_status = "SUCCESS"
                    return content

                usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
                details = usage.get("completion_tokens_details")
                details = details if isinstance(details, dict) else {}
                exhaustion = _reasoning_exhausted(choice, data, config["max_tokens"])
                _LOG.warning(
                    "OPENROUTER_EMPTY_RESPONSE model=%s stage=%s attempt=%s "
                    "finish_reason=%s max_tokens=%s completion_tokens=%s "
                    "reasoning_tokens=%s reasoning_exhausted=%s reasoning_config=%s "
                    "provider=%s generation_id=%s duration_ms=%.1f",
                    candidate, stage, attempt + 1, choice.get("finish_reason"),
                    config["max_tokens"], usage.get("completion_tokens"),
                    details.get("reasoning_tokens"), exhaustion, config.get("reasoning"),
                    data.get("provider"), data.get("id"), (perf_counter() - started) * 1000,
                )
                request_status = "EMPTY_RESPONSE"
                error_code = "REASONING_EXHAUSTED" if exhaustion else "EMPTY_RESPONSE"
                last_error = OpenRouterError(
                    f"OpenRouter retornou resposta vazia (HTTP {response.status_code}, "
                    f"modelo {candidate}, finish_reason={choice.get('finish_reason')}, "
                    f"max_tokens={config['max_tokens']})."
                )
                if attempt == 0:
                    # For DeepSeek V4.1, cap thinking instead of increasing the
                    # total output budget. This also covers providers which ignore
                    # enabled=False while still reporting reasoning exhaustion.
                    # Bigger budget and lower effort if thinking ate the answer;
                    # a single ordinary retry for unexplained transient empties.
                    # Some MiMo providers omit reasoning token breakdowns. A
                    # length-truncated empty answer is enough to try the capped
                    # thinking configuration once, without repeating the same call.
                    recovery = exhaustion or (
                        _mimo_v26_pro(candidate) and choice.get("finish_reason") == "length"
                    )
                    continue
                break
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
                    f"OpenRouter HTTP {status}, modelo {candidate}: "
                    f"{str(detail)[:500] or 'requisição rejeitada'}"
                )
                # Unsupported reasoning options: retry once without that hint.
                # A normal HTTP 400 (wrong model ID, unavailable params, etc.)
                # must not trigger an expensive blind token-budget increase.
                if status == 400 and "reasoning" in config and attempt == 0:
                    # DeepSeek may reject disabling thinking; cap reasoning
                    # instead. Other providers retry without the unsupported hint.
                    if _deepseek_v41_flash(candidate):
                        recovery = True
                    else:
                        remove_reasoning = True
                        recovery = False
                    continue
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
