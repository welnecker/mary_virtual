from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st


RELATIONSHIP_EVENT_COMPACTION_VERSION = (
    "relationship-event-compaction-v1-non-recursive-snapshots"
)
MAX_EVENTS = 24
MAX_TEXT = 520
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _text(value: Any, limit: int = MAX_TEXT) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def _compact_mapping(value: Any, *, depth: int = 0) -> Any:
    if depth >= 3:
        if isinstance(value, (dict, list, tuple, set)):
            return None
        return _text(value, 240) if isinstance(value, str) else value
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            if name in {
                "events",
                "relationship_snapshot",
                "debug_context",
                "raw_messages",
                "raw_system_prompt",
                "prompt",
                "messages",
                "history",
                "recent_messages",
                "continuation_context",
            }:
                continue
            compact = _compact_mapping(item, depth=depth + 1)
            if compact is not None:
                result[name] = compact
        return result
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in list(value)[-12:]:
            compact = _compact_mapping(item, depth=depth + 1)
            if compact is not None:
                result.append(compact)
        return result
    if isinstance(value, str):
        return _text(value)
    return value


def criar_snapshot_relacao_compacto(estado: dict[str, Any]) -> dict[str, Any]:
    state = estado if isinstance(estado, dict) else {}
    keep = {
        "emotional_stage",
        "sexual_level",
        "familiarity_level",
        "trust_level",
        "affection_level",
        "romantic_tension_level",
        "mary_desire_level",
        "mary_curiosity_level",
        "initiative_drive",
        "interaction_count",
        "sexual_state",
        "scenario_context",
        "mary_internal_state",
        "experience_state",
        "voice_state",
    }
    snapshot = {
        key: _compact_mapping(value)
        for key, value in state.items()
        if key in keep
    }
    return snapshot


def _compact_event(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    event = deepcopy(value)
    event.pop("relationship_snapshot", None)
    event.pop("debug_context", None)
    event["user_text"] = _text(event.get("user_text"), 360)
    event["mary_response"] = _text(event.get("mary_response"), 520)
    for field in ("direction", "signals"):
        compact = _compact_mapping(event.get(field))
        event[field] = compact if isinstance(compact, dict) else {}
    return event


def compactar_estado_relacao(value: Any) -> dict[str, Any]:
    state = deepcopy(value) if isinstance(value, dict) else {}
    raw_events = state.get("events")
    events: list[dict[str, Any]] = []
    if isinstance(raw_events, list):
        for item in raw_events[-MAX_EVENTS:]:
            compact = _compact_event(item)
            if compact is not None:
                events.append(compact)
    state["events"] = events
    active = state.get("active_turn")
    if isinstance(active, dict):
        active = deepcopy(active)
        active.pop("relationship_snapshot", None)
        active["user_text"] = _text(active.get("user_text"), 360)
        active["mary_response"] = _text(active.get("mary_response"), 520)
        active["direction"] = _compact_mapping(active.get("direction")) or {}
        active["signals"] = _compact_mapping(active.get("signals")) or {}
        state["active_turn"] = active
    return state


def _patch_snapshot(module: Any) -> None:
    current = getattr(module, "criar_snapshot_relacao", None)
    if callable(current) and not getattr(current, "_mary_non_recursive_snapshot", False):
        criar_snapshot_relacao_compacto._mary_non_recursive_snapshot = True  # type: ignore[attr-defined]
        setattr(module, "criar_snapshot_relacao", criar_snapshot_relacao_compacto)


def _patch_event_registration(module: Any) -> None:
    original = getattr(module, "registrar_evento_estado_relacao", None)
    if not callable(original) or getattr(original, "_mary_event_compaction_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        adjusted = dict(kwargs)
        if "relationship_state" in adjusted:
            adjusted["relationship_state"] = compactar_estado_relacao(
                adjusted.get("relationship_state")
            )
        result = original(*args, **adjusted)
        return compactar_estado_relacao(result)

    wrapper._mary_event_compaction_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "registrar_evento_estado_relacao", wrapper)


def _patch_get_states(module: Any) -> None:
    original = getattr(module, "obter_estados_relacao", None)
    if not callable(original) or getattr(original, "_mary_state_compaction_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        if not isinstance(result, tuple) or not result:
            return result
        relationship = compactar_estado_relacao(result[0])
        sexual = relationship.get("sexual_state")
        if not isinstance(sexual, dict):
            sexual = result[1] if len(result) > 1 and isinstance(result[1], dict) else {}
            relationship["sexual_state"] = sexual
        st.session_state["relationship_state"] = relationship
        return relationship, sexual

    wrapper._mary_state_compaction_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "obter_estados_relacao", wrapper)


def aplicar_compactacao_eventos_relacao() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    current = st.session_state.get("relationship_state")
    if isinstance(current, dict):
        st.session_state["relationship_state"] = compactar_estado_relacao(current)
    _patch_snapshot(module)
    _patch_event_registration(module)
    _patch_get_states(module)


def install_relationship_event_compaction() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_compactacao_eventos_relacao()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "RELATIONSHIP_EVENT_COMPACTION_VERSION",
    "aplicar_compactacao_eventos_relacao",
    "compactar_estado_relacao",
    "criar_snapshot_relacao_compacto",
    "install_relationship_event_compaction",
]
