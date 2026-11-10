"""Passive per-request OpenRouter accounting; never calls an LLM or persists prompts."""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

_CONTEXT: ContextVar[dict] = ContextVar("mary_token_context", default={})
_SINK: ContextVar[Callable[[dict], None] | None] = ContextVar("mary_token_sink", default=None)


def begin_turn(*, sink: Callable[[dict], None], run_id: str, seq: int,
               chapter_id: str, line_order: int = 0) -> None:
    """Enable collection for this Streamlit script run, including early input routing."""
    _CONTEXT.set({
        "run_id": str(run_id or ""), "seq": int(seq or 0),
        "chapter_id": str(chapter_id or ""), "line_order": int(line_order or 0),
    })
    _SINK.set(sink)


def update_line_order(order: int) -> None:
    context = _CONTEXT.get()
    if context:
        _CONTEXT.set({**context, "line_order": int(order or 0)})


def classify_call(filename: str, *, call_type: str = "") -> str:
    if call_type:
        return call_type
    stem = Path(filename).stem
    return {
        "input_router": "INPUT_ROUTER",
        "user_understanding_audit": "USER_UNDERSTANDING",
        "direct_semantic_director": "SEMANTIC_DIRECTOR",
        "conversation_state": "CONVERSATION_STATE",
        "director": "SCENE_DIRECTOR",
        "episodic_memory_shadow": "EPISODIC_MEMORY",
    }.get(stem, "REDACTOR" if stem == "app" else stem.upper())


def make_usage_event(*, model: str, call_type: str, attempt: int,
                     duration_ms: float, status: str, http_status: int | None,
                     request_messages: list[dict], response: dict | None,
                     error_code: str = "") -> dict:
    """Return numeric provider data when present, blanks otherwise (never guessed)."""
    data = response if isinstance(response, dict) else {}
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    prompt_details = prompt_details if isinstance(prompt_details, dict) else {}
    completion_details = completion_details if isinstance(completion_details, dict) else {}
    context = _CONTEXT.get()
    return {
        "event_id": uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": context.get("run_id", ""),
        "seq": context.get("seq", 0),
        "chapter_id": context.get("chapter_id", ""),
        "line_order": context.get("line_order", 0),
        "call_type": call_type,
        "model": str(data.get("model") or model),
        "attempt": int(attempt),
        "status": status,
        "http_status": http_status if http_status is not None else "",
        "prompt_tokens": usage.get("prompt_tokens", ""),
        "completion_tokens": usage.get("completion_tokens", ""),
        "total_tokens": usage.get("total_tokens", ""),
        "reasoning_tokens": completion_details.get("reasoning_tokens", ""),
        "cached_tokens": prompt_details.get("cached_tokens", ""),
        "cost_usd": usage.get("cost", ""),
        "duration_ms": round(duration_ms, 1),
        "request_chars": sum(len(str(msg.get("content") or "")) for msg in request_messages if isinstance(msg, dict)),
        "error_code": str(error_code or "")[:100],
    }


def record(event: dict) -> None:
    """Accounting must never interfere with a successful narrative response."""
    sink = _SINK.get()
    if sink is not None:
        try:
            sink(event)
        except Exception:
            pass
