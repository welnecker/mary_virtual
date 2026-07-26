from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any

import streamlit as st

import scenarios.card_runtime as card_runtime
import ui.card_runtime_integration as card_integration
from scenarios.stories.casada_frustrada.beat_engine import (
    inicializar_estado_beats,
    obter_beat_atual,
    sincronizar_beat_apos_resposta,
)
from scenarios.stories.casada_frustrada.compact_prompt import compilar_prompt_beat


BEAT_RUNTIME_VERSION = "casada-frustrada-beat-runtime-v1-compact-authority"
_INSTALLED = False


def _text(value: Any) -> str:
    return str(value or "").strip()


def _instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    if not isinstance(value, dict):
        return None
    if _text(value.get("scenario_id")) != "casada_frustrada":
        return None
    return value


def _last_assistant_message() -> str:
    messages = st.session_state.get("messages")
    if not isinstance(messages, list):
        return ""
    for item in reversed(messages):
        if isinstance(item, dict) and item.get("role") == "assistant":
            content = _text(item.get("content"))
            if content:
                return content
    return ""


def _sexual_state() -> dict[str, Any]:
    relationship = st.session_state.get("relationship_state")
    if not isinstance(relationship, dict):
        return {}
    value = relationship.get("sexual_state")
    return deepcopy(value) if isinstance(value, dict) else {}


def _sync_before_turn() -> None:
    instance = _instance()
    if not isinstance(instance, dict):
        return

    scene = instance.get("scene_state")
    scene = inicializar_estado_beats(scene if isinstance(scene, dict) else {})
    scene = sincronizar_beat_apos_resposta(
        scene_state=scene,
        sexual_state=_sexual_state(),
        last_mary_response=_last_assistant_message(),
    )
    beat = obter_beat_atual(scene)
    if beat:
        route = _text(beat.get("route"))
        beat_id = _text(beat.get("id"))
        scene["current_route"] = route
        scene["current_beat"] = beat_id
        instance["current_route"] = route
        instance["current_beat"] = beat_id
        if beat.get("sexual_phase") in {"active", "climax", "aftercare"}:
            scene["sexual_scene_phase"] = beat.get("sexual_phase")
            scene["seduction_level"] = max(
                int(beat.get("intensity", 0) or 0),
                int(scene.get("seduction_level", 0) or 0),
            )

    instance["scene_state"] = scene
    st.session_state["scenario_instance"] = instance

    relationship = st.session_state.get("relationship_state")
    if isinstance(relationship, dict) and beat:
        relationship = deepcopy(relationship)
        scenario = relationship.get("scenario")
        scenario = deepcopy(scenario) if isinstance(scenario, dict) else {}
        scenario.update(
            {
                "active": True,
                "scenario_id": "casada_frustrada",
                "scenario_route": beat.get("route"),
                "scenario_beat": beat.get("id"),
            }
        )
        relationship["scenario"] = scenario
        st.session_state["relationship_state"] = relationship


def _compact_window(scenario_id: str, route: str) -> str:
    if _text(scenario_id) != "casada_frustrada":
        return _ORIGINAL_WINDOW(scenario_id, route)
    instance = _instance()
    scene = instance.get("scene_state") if isinstance(instance, dict) else {}
    scene = scene if isinstance(scene, dict) else {}
    return compilar_prompt_beat(
        scene_state=scene,
        sexual_state=_sexual_state(),
        last_mary_response=_last_assistant_message(),
    )


def _patch_process() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    current = getattr(module, "processar_interacao", None)
    if not callable(current) or getattr(current, "_mary_beat_runtime", False):
        return

    @wraps(current)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        _sync_before_turn()
        return current(*args, **kwargs)

    wrapper._mary_beat_runtime = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def _patch_prompt_window() -> None:
    if getattr(card_integration.montar_janela_roteiro, "_mary_compact_beat_window", False):
        return
    _compact_window._mary_compact_beat_window = True  # type: ignore[attr-defined]
    card_runtime.montar_janela_roteiro = _compact_window
    card_integration.montar_janela_roteiro = _compact_window


def _patch_card_restrictions() -> None:
    current = card_runtime.aplicar_restricoes_card
    if getattr(current, "_mary_beat_authority", False):
        return

    @wraps(current)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = current(*args, **kwargs)
        if _text(kwargs.get("scenario_id")) != "casada_frustrada":
            return result
        instance = _instance()
        scene = instance.get("scene_state") if isinstance(instance, dict) else {}
        beat = obter_beat_atual(scene if isinstance(scene, dict) else {})
        if not beat:
            return result

        result = deepcopy(result) if isinstance(result, dict) else {}
        direction = result.get("turn_direction")
        direction = deepcopy(direction) if isinstance(direction, dict) else {}
        intensity = int(beat.get("intensity", 0) or 0)
        sexual_allowed = intensity >= 2 or beat.get("sexual_phase") in {
            "tension",
            "active",
            "climax",
            "aftercare",
        }
        direction.update(
            {
                "primary_intention": _text(beat.get("objective")),
                "experience_mode": "continue_shared_fantasy",
                "response_scope": "brief",
                "avoid_question": True,
                "beat_authority": True,
                "sexual_expression_allowed": sexual_allowed,
                "explicit_sexual_language_allowed": intensity >= 3,
            }
        )
        result["turn_direction"] = direction
        return result

    wrapper._mary_beat_authority = True  # type: ignore[attr-defined]
    card_runtime.aplicar_restricoes_card = wrapper
    card_integration.aplicar_restricoes_card = wrapper


def install_casada_frustrada_beat_runtime() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _patch_prompt_window()
    _patch_card_restrictions()
    _patch_process()
    _INSTALLED = True


_ORIGINAL_WINDOW = card_runtime.montar_janela_roteiro


__all__ = [
    "BEAT_RUNTIME_VERSION",
    "install_casada_frustrada_beat_runtime",
]
