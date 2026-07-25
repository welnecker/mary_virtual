from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st

import ui.scenario_menu as scenario_menu
from repositories.scenario_session_repository import salvar_instancia_cenario
from scenarios.card_runtime import aplicar_restricoes_card, montar_janela_roteiro


CARD_RUNTIME_INTEGRATION_VERSION = (
    "card-runtime-integration-v1-screenplay-constraints-history"
)
_RECENT_MESSAGES_LIMIT = 20
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    return value if isinstance(value, dict) else None


def _context() -> tuple[str, str]:
    instance = _instance()
    if not isinstance(instance, dict):
        return "", ""
    scene = instance.get("scene_state")
    if not isinstance(scene, dict):
        scene = {}
    return (
        _text(instance.get("scenario_id")),
        _text(instance.get("current_route") or scene.get("current_route")),
    )


def _valid_messages(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("role"))
        content = _text(item.get("content"))
        if role in {"user", "assistant"} and content:
            result.append({"role": role, "content": content})
    return result


def _persist_recent_messages() -> None:
    instance = _instance()
    if not isinstance(instance, dict):
        return
    messages = _valid_messages(st.session_state.get("messages"))[-_RECENT_MESSAGES_LIMIT:]
    progress = instance.get("story_progress")
    if not isinstance(progress, dict):
        progress = {}
    progress = deepcopy(progress)
    progress["recent_messages"] = messages
    progress["recent_messages_session_id"] = _text(
        instance.get("scenario_session_id")
    )
    instance["story_progress"] = progress
    st.session_state["scenario_instance"] = instance
    try:
        salvar_instancia_cenario(instance)
    except Exception:
        # A conversa não deve cair por falha secundária de persistência.
        pass


def _fallback_messages(instance: dict[str, Any], messages: Any) -> list[dict[str, str]]:
    current = _valid_messages(messages)
    if current:
        return current[-_RECENT_MESSAGES_LIMIT:]
    progress = instance.get("story_progress")
    if isinstance(progress, dict):
        stored_session = _text(progress.get("recent_messages_session_id"))
        current_session = _text(instance.get("scenario_session_id"))
        if not stored_session or stored_session == current_session:
            restored = _valid_messages(progress.get("recent_messages"))
            if restored:
                return restored[-_RECENT_MESSAGES_LIMIT:]
    scene = instance.get("scene_state")
    if isinstance(scene, dict):
        restored = _valid_messages(scene.get("continuation_context"))
        if restored:
            return restored[-_RECENT_MESSAGES_LIMIT:]
    return []


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(original, "_mary_card_runtime_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        scenario_id, route = _context()
        if not scenario_id or not route:
            return str(original(*args, **kwargs) or "")
        aligned = dict(kwargs)
        constrained = aplicar_restricoes_card(
            scenario_id=scenario_id,
            route=route,
            mary_profile=aligned.get("mary_profile"),
            relationship_state=aligned.get("relationship_state"),
            sexual_state=aligned.get("sexual_state"),
            turn_intent=aligned.get("turn_intent"),
            turn_direction=aligned.get("turn_direction"),
        )
        aligned.update(constrained)
        aligned["include_voice_examples"] = False
        base = str(original(*args, **aligned) or "").strip()
        screenplay = montar_janela_roteiro(scenario_id, route)
        return "\n\n".join(part for part in (base, screenplay) if part)

    wrapper._mary_card_runtime_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def _patch_process_interaction(module: Any) -> None:
    original = getattr(module, "processar_interacao", None)
    if not callable(original) or getattr(original, "_mary_card_process_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        scenario_id, route = _context()
        if scenario_id and route:
            relationship = st.session_state.get("relationship_state")
            sexual = relationship.get("sexual_state") if isinstance(relationship, dict) else {}
            constrained = aplicar_restricoes_card(
                scenario_id=scenario_id,
                route=route,
                mary_profile=st.session_state.get("mary_profile"),
                relationship_state=relationship,
                sexual_state=sexual,
                turn_intent=(relationship or {}).get("current_turn_intent")
                if isinstance(relationship, dict)
                else {},
                turn_direction=(relationship or {}).get("current_turn_direction")
                if isinstance(relationship, dict)
                else {},
            )
            st.session_state["relationship_state"] = constrained["relationship_state"]
        result = original(*args, **kwargs)
        _persist_recent_messages()
        return result

    wrapper._mary_card_process_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def _wrap_continue(original: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(original, "_mary_card_continue_wrapped", False):
        return original

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        if not isinstance(result, tuple) or len(result) < 2:
            return result
        instance, messages = result[0], result[1]
        if not isinstance(instance, dict):
            return result
        restored = _fallback_messages(instance, messages)
        return instance, restored

    wrapper._mary_card_continue_wrapped = True  # type: ignore[attr-defined]
    return wrapper


def _patch_continue(module: Any) -> None:
    original = getattr(module, "continuar_cenario_para_usuario", None)
    if callable(original):
        wrapped = _wrap_continue(original)
        setattr(module, "continuar_cenario_para_usuario", wrapped)
        scenario_menu.continuar_cenario_para_usuario = wrapped


def aplicar_card_runtime() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_prompt_builder(module)
    _patch_process_interaction(module)
    _patch_continue(module)


def install_card_runtime_integration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_card_runtime()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CARD_RUNTIME_INTEGRATION_VERSION",
    "aplicar_card_runtime",
    "install_card_runtime_integration",
]
