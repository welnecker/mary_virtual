from __future__ import annotations

import sys
from copy import deepcopy
from typing import Any, Callable

import streamlit as st


APP_RUNTIME_INTEGRATION_VERSION = "app-runtime-integration-v1-adaptive-pacing"

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _resolve_duration() -> dict[str, int | bool]:
    instance = st.session_state.get("scenario_instance")
    config: dict[str, Any] = {}
    if isinstance(instance, dict):
        candidate = instance.get("scenario_config")
        if isinstance(candidate, dict):
            config = candidate

    duration = config.get("duration")
    if not isinstance(duration, dict):
        duration = {}

    target = max(1, _safe_int(duration.get("target_interactions"), 40))
    soft_start = max(
        1,
        _safe_int(duration.get("soft_ending_start"), max(1, target - 8)),
    )
    hard_limit = max(
        soft_start + 1,
        _safe_int(duration.get("hard_ending_limit"), max(target + 10, 58)),
    )
    ending_turns = max(1, _safe_int(duration.get("ending_turns"), 2))

    return {
        "target": target,
        "soft_start": soft_start,
        "hard_limit": hard_limit,
        "ending_turns": ending_turns,
        "count_is_advisory": bool(duration.get("count_is_advisory", True)),
        "allow_early_resolution": bool(duration.get("allow_early_resolution", True)),
    }


def _scene_has_progress(scene_state: dict[str, Any]) -> bool:
    if bool(scene_state.get("ending_ready") or scene_state.get("climax_reached")):
        return True
    resolved = scene_state.get("resolved_elements")
    if isinstance(resolved, list) and resolved:
        return True
    completed = scene_state.get("completed_beats")
    if isinstance(completed, list) and completed:
        return True
    return bool(
        str(scene_state.get("current_phase") or "").strip().lower()
        in {"climax", "aftercare", "ending"}
    )


def _scene_is_repetitive(scene_state: dict[str, Any]) -> bool:
    same_activity_turns = _safe_int(scene_state.get("same_activity_turns"), 0)
    repeated_turns = _safe_int(scene_state.get("repeated_turns"), 0)
    stalled_turns = _safe_int(scene_state.get("stalled_turns"), 0)
    return max(same_activity_turns, repeated_turns, stalled_turns) >= 3


def aplicar_politica_adaptativa_encerramento(
    *,
    scene_state: dict[str, Any],
    interaction_number: int,
) -> dict[str, Any]:
    """Substitui o antigo corte 45/50 por janela narrativa configurável.

    A contagem orienta o ritmo. Encerramento forçado só ocorre no teto de
    segurança e, antes dele, apenas sinais de resolução ou repetição autorizam
    a preparação do final.
    """

    state = deepcopy(scene_state if isinstance(scene_state, dict) else {})
    count = max(0, _safe_int(interaction_number, 0))
    duration = _resolve_duration()
    soft_start = int(duration["soft_start"])
    target = int(duration["target"])
    hard_limit = int(duration["hard_limit"])
    ending_turns = int(duration["ending_turns"])

    if bool(state.get("ending_sent", False)):
        return state

    requested = bool(state.get("ending_requested_by_user", False))
    requested_at = _safe_int(state.get("ending_requested_at_interaction"), 0)
    if requested and count > requested_at:
        state.update(
            {
                "current_phase": "ending",
                "ending_ready": True,
                "ending_forced": True,
                "ending_trigger": "user_button",
                "ending_trigger_interaction": count,
                "ending_countdown_visible": False,
                "ending_countdown_remaining": 0,
            }
        )
        return state

    progress = _scene_has_progress(state)
    repetitive = _scene_is_repetitive(state)

    if count >= hard_limit:
        state.update(
            {
                "current_phase": "ending",
                "ending_ready": True,
                "ending_forced": True,
                "ending_trigger": "safety_limit",
                "ending_trigger_interaction": count,
                "ending_countdown_visible": False,
                "ending_countdown_remaining": 0,
            }
        )
        return state

    if count >= target and (progress or repetitive):
        state.update(
            {
                "ending_ready": True,
                "ending_forced": False,
                "ending_trigger": (
                    "narrative_resolution" if progress else "repetition_guard"
                ),
                "ending_trigger_interaction": count,
                "ending_countdown_visible": True,
                "ending_countdown_remaining": ending_turns,
                "ending_pressure": "adaptive",
            }
        )
        return state

    if count >= soft_start:
        state.update(
            {
                "ending_countdown_visible": True,
                "ending_countdown_remaining": max(1, hard_limit - count),
                "ending_pressure": "soft",
                "seek_narrative_resolution": True,
                "avoid_repetition": True,
            }
        )
    else:
        state.update(
            {
                "ending_countdown_visible": False,
                "ending_countdown_remaining": 0,
                "seek_narrative_resolution": False,
                "avoid_repetition": True,
            }
        )

    return state


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(original, "_mary_runtime_wrapped", False):
        return

    def wrapper(*args: Any, **kwargs: Any) -> str:
        instance = st.session_state.get("scenario_instance")
        scene_state: dict[str, Any] = {}
        if isinstance(instance, dict):
            candidate = instance.get("scene_state")
            if isinstance(candidate, dict):
                scene_state = candidate

        messages = st.session_state.get("messages")
        recent_messages = messages[-8:] if isinstance(messages, list) else []

        last_mary_response = ""
        for item in reversed(recent_messages):
            if isinstance(item, dict) and item.get("role") == "assistant":
                last_mary_response = str(item.get("content") or "").strip()
                break

        relationship_state = kwargs.get("relationship_state")
        active_turn = (
            relationship_state.get("active_turn")
            if isinstance(relationship_state, dict)
            else {}
        )
        user_message = ""
        if isinstance(active_turn, dict):
            user_message = str(active_turn.get("user_text") or "").strip()

        kwargs.setdefault("scene_state", scene_state)
        kwargs.setdefault("recent_messages", recent_messages)
        kwargs.setdefault("last_mary_response", last_mary_response)
        kwargs.setdefault("user_message", user_message)
        return original(*args, **kwargs)

    wrapper._mary_runtime_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def aplicar_integracao_runtime() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return

    setattr(module, "aplicar_politica_encerramento_por_interacoes", aplicar_politica_adaptativa_encerramento)

    duration = _resolve_duration()
    setattr(module, "ENDING_COUNTDOWN_START", int(duration["soft_start"]))
    setattr(module, "ENDING_INTERACTION_LIMIT", int(duration["hard_limit"]))

    _patch_prompt_builder(module)


def install_app_runtime_integration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_integracao_runtime()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "APP_RUNTIME_INTEGRATION_VERSION",
    "aplicar_integracao_runtime",
    "aplicar_politica_adaptativa_encerramento",
    "install_app_runtime_integration",
]
