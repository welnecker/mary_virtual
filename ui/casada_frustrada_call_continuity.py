from __future__ import annotations

from copy import deepcopy
from functools import wraps
import re
import sys
import unicodedata
from typing import Any

import streamlit as st

import scenarios.card_runtime as card_runtime
import ui.card_runtime_integration as card_integration


CALL_CONTINUITY_VERSION = "casada-frustrada-call-continuity-v1-established-video"
_INSTALLED = False

_CAMERA_EVIDENCE = (
    "ta me vendo",
    "consegue me ver",
    "celular aqui na bancada",
    "celular na bancada",
    "celular aqui na pia",
    "celular na pia",
    "apoiar o celular",
    "apoiei o celular",
    "da pra ver dai",
    "voce viu",
    "me olha",
    "olha pra mim",
)

_VISUAL_INTIMACY_EVIDENCE = (
    "tirando a calca",
    "tirar a calca",
    "so de calcinha",
    "calcinha de renda",
    "tirar o vestido",
    "tirar o sutia",
    "sem sutia",
    "tirar a cueca",
    "sem cueca",
    "vendo o seu corpo",
    "vendo voce",
)

_ACTIVE_SEXUAL_EVIDENCE = (
    "me masturb",
    "se masturb",
    "dedos por baixo",
    "to molhada",
    "estou molhada",
    "clitoris",
    "buceta",
    "xoxota",
    "pau",
    "rola",
    "punheta",
    "gozar",
    "gozo",
    "gemido",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _recent_text(prompt: Any = "") -> str:
    messages = st.session_state.get("messages")
    parts: list[str] = []
    if isinstance(messages, list):
        for item in messages[-14:]:
            if isinstance(item, dict):
                parts.append(_text(item.get("content")))
    parts.append(_text(prompt))
    return _normalize("\n".join(parts))


def _active_instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    if not isinstance(value, dict):
        return None
    if _text(value.get("scenario_id")) != "casada_frustrada":
        return None
    return value


def _call_evidence(prompt: Any = "") -> tuple[bool, bool, bool]:
    text = _recent_text(prompt)
    camera = _contains_any(text, _CAMERA_EVIDENCE)
    visual = _contains_any(text, _VISUAL_INTIMACY_EVIDENCE)
    sexual = _contains_any(text, _ACTIVE_SEXUAL_EVIDENCE)
    return camera, visual, sexual


def _reconcile_active_call(prompt: Any = "") -> None:
    instance = _active_instance()
    if not isinstance(instance, dict):
        return

    camera, visual, sexual = _call_evidence(prompt)
    if not (camera or visual or sexual):
        return

    current_route = _text(instance.get("current_route"))
    scene = instance.get("scene_state")
    scene = deepcopy(scene) if isinstance(scene, dict) else {}
    current_route = current_route or _text(scene.get("current_route"))

    # Esta correção vale para a conversa remota. Não recua encontro físico para chamada.
    if current_route not in {"messages", "hidden_call"}:
        return

    beat = "mutual_arousal" if sexual else "visual_escalation" if visual else "visual_contact"
    previous_route = current_route

    scene.update(
        {
            "previous_route": previous_route,
            "current_route": "hidden_call",
            "current_phase": "intimacy" if sexual else "tension",
            "current_beat": beat,
            "phone_numbers_exchanged": True,
            "phone_contact_started": True,
            "privacy_established": True,
            "video_call_established": True,
            "camera_active": True,
            "sexual_scene_phase": "active" if sexual else "tension",
            "sexual_voice_mode": "explicit_direct" if sexual else "intimate_direct",
            "seduction_level": max(4 if sexual else 3, int(scene.get("seduction_level", 0) or 0)),
            "last_route_transition_reason": "confirmed_active_video_call",
            "dialogue_bridge_active_this_turn": False,
        }
    )

    sexual_state = scene.get("sexual_state")
    sexual_state = deepcopy(sexual_state) if isinstance(sexual_state, dict) else {}
    if sexual:
        sexual_state.update(
            {
                "scene_phase": "active",
                "arousal_level": max(0.72, float(sexual_state.get("arousal_level", 0.0) or 0.0)),
                "stimulation_turns": max(2, int(sexual_state.get("stimulation_turns", 0) or 0)),
                "frustration_state": sexual_state.get("frustration_state", "") or "",
            }
        )
    elif _text(sexual_state.get("scene_phase")) in {"", "idle", "none", "inactive"}:
        sexual_state.update(
            {
                "scene_phase": "active",
                "arousal_level": max(0.45, float(sexual_state.get("arousal_level", 0.0) or 0.0)),
                "stimulation_turns": max(1, int(sexual_state.get("stimulation_turns", 0) or 0)),
            }
        )
    scene["sexual_state"] = sexual_state

    instance["previous_route"] = previous_route
    instance["current_route"] = "hidden_call"
    instance["current_phase"] = scene["current_phase"]
    instance["current_beat"] = beat
    instance["scene_state"] = scene
    st.session_state["scenario_instance"] = instance

    relationship = st.session_state.get("relationship_state")
    relationship = deepcopy(relationship) if isinstance(relationship, dict) else {}
    relationship["sexual_level"] = max(4 if sexual else 3, int(relationship.get("sexual_level", 0) or 0))
    relationship["sexual_intimacy"] = max(0.75 if sexual else 0.5, float(relationship.get("sexual_intimacy", 0.0) or 0.0))
    relationship["sexual_state"] = deepcopy(sexual_state)
    scenario = relationship.get("scenario")
    scenario = deepcopy(scenario) if isinstance(scenario, dict) else {}
    scenario.update(
        {
            "active": True,
            "scenario_id": "casada_frustrada",
            "scenario_route": "hidden_call",
            "scenario_phase": scene["current_phase"],
            "scenario_beat": beat,
        }
    )
    relationship["scenario"] = scenario
    st.session_state["relationship_state"] = relationship


def _patch_card_restrictions() -> None:
    original = card_runtime.aplicar_restricoes_card
    if getattr(original, "_mary_call_intensity_fix", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original(*args, **kwargs)
        route = _text(kwargs.get("route"))
        scenario_id = _text(kwargs.get("scenario_id"))
        if scenario_id != "casada_frustrada" or route != "hidden_call":
            return result

        result = deepcopy(result) if isinstance(result, dict) else {}
        direction = result.get("turn_direction")
        direction = deepcopy(direction) if isinstance(direction, dict) else {}
        direction.update(
            {
                "sexual_expression_allowed": True,
                "explicit_sexual_language_allowed": True,
                "romantic_expression_allowed": True,
                "experience_mode": "continue_shared_fantasy",
                "primary_intention": (
                    "Continuar a chamada de vídeo exatamente do ponto já vivido, "
                    "com intensidade crescente e sem pedir vídeo novamente."
                ),
                "voice_register": "popular, íntimo, direto e sexualmente explícito",
                "avoid_question": True,
            }
        )
        result["turn_direction"] = direction

        relationship = result.get("relationship_state")
        relationship = deepcopy(relationship) if isinstance(relationship, dict) else {}
        relationship["sexual_level"] = max(3, int(relationship.get("sexual_level", 0) or 0))
        sexual = result.get("sexual_state")
        sexual = deepcopy(sexual) if isinstance(sexual, dict) else {}
        if _text(sexual.get("scene_phase")) in {"", "idle", "none", "inactive"}:
            sexual.update(
                {
                    "scene_phase": "active",
                    "arousal_level": max(0.45, float(sexual.get("arousal_level", 0.0) or 0.0)),
                    "stimulation_turns": max(1, int(sexual.get("stimulation_turns", 0) or 0)),
                }
            )
        relationship["sexual_state"] = deepcopy(sexual)
        result["relationship_state"] = relationship
        result["sexual_state"] = sexual
        return result

    wrapper._mary_call_intensity_fix = True  # type: ignore[attr-defined]
    card_runtime.aplicar_restricoes_card = wrapper
    card_integration.aplicar_restricoes_card = wrapper


def _patch_process() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    current = getattr(module, "processar_interacao", None)
    if not callable(current) or getattr(current, "_mary_call_continuity", False):
        return

    @wraps(current)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        prompt = kwargs.get("prompt")
        if prompt is None and args:
            prompt = args[0]
        _reconcile_active_call(prompt)
        return current(*args, **kwargs)

    wrapper._mary_call_continuity = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def install_casada_frustrada_call_continuity() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _patch_card_restrictions()
    _patch_process()
    _INSTALLED = True


__all__ = [
    "CALL_CONTINUITY_VERSION",
    "install_casada_frustrada_call_continuity",
]
