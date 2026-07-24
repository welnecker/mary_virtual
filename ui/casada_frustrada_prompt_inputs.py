from __future__ import annotations

import sys
from copy import deepcopy
from functools import wraps
from typing import Any, Callable

import streamlit as st

from scenarios.stories.casada_frustrada.screenplay import SCENARIO_ID


CASADA_FRUSTRADA_PROMPT_INPUTS_VERSION = (
    "casada-frustrada-prompt-inputs-v1-route-aligned"
)

_SUPERMARKET_ROUTES = {
    "supermarket_encounter",
    "aisle_flirtation",
    "phone_exchange",
}

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _scenario_context() -> tuple[str, str]:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return "", ""
    scene_state = instance.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}
    scenario_id = str(instance.get("scenario_id") or "").strip()
    route = str(instance.get("current_route") or scene_state.get("current_route") or "").strip()
    return scenario_id, route


def _aligned_direction(route: str, current: Any) -> dict[str, Any]:
    direction = deepcopy(current) if isinstance(current, dict) else {}
    direction["experience_mode"] = "natural_conversation"
    direction["voice_register"] = "natural"
    direction["avoid_question"] = True
    direction["should_reveal"] = False

    if route == "supermarket_encounter":
        direction.update(
            {
                "primary_intention": "respond_briefly_inside_first_contact",
                "emotional_color": "hesitant_embarrassed_curious",
                "should_lead": False,
                "response_scope": "brief",
            }
        )
    elif route == "aisle_flirtation":
        direction.update(
            {
                "primary_intention": "cultivate_interest_with_screenplay_language",
                "emotional_color": "needy_hesitant_increasingly_interested",
                "should_lead": True,
                "response_scope": "brief",
            }
        )
    elif route == "phone_exchange":
        direction.update(
            {
                "primary_intention": "avoid_losing_contact",
                "emotional_color": "nervous_impulsive_and_hopeful",
                "should_lead": True,
                "response_scope": "brief",
            }
        )
    elif route == "messages":
        direction.update(
            {
                "primary_intention": "resume_contact_with_anxiety_and_desire",
                "emotional_color": "anxious_cautious_needy",
                "should_lead": True,
            }
        )
    elif route == "hidden_call":
        direction.update(
            {
                "primary_intention": "intensify_desire_from_the_current_action",
                "emotional_color": "cautious_hungry_and_aroused",
                "should_lead": True,
            }
        )
    elif route == "secret_meeting_plan":
        direction.update(
            {
                "primary_intention": "make_the_secret_meeting_concrete",
                "emotional_color": "afraid_excited_and_decided",
                "should_lead": True,
            }
        )
    elif route in {"secret_meeting", "growing_tension"}:
        direction.update(
            {
                "primary_intention": "live_one_immediate_screenplay_movement",
                "emotional_color": "trembling_hungry_and_urgent",
                "should_lead": True,
            }
        )
    elif route in {"intimacy", "climax"}:
        direction.update(
            {
                "primary_intention": "react_from_the_body_with_screenplay_vocabulary",
                "emotional_color": "ardent_explicit_and_overwhelmed",
                "voice_register": "explicit",
                "should_lead": True,
            }
        )
    elif route in {"aftercare", "future_secret"}:
        direction.update(
            {
                "primary_intention": "remain_vulnerable_and_present",
                "emotional_color": "exhausted_vulnerable_and_satisfied",
                "should_lead": False,
            }
        )
    return direction


def _aligned_intent(route: str, current: Any) -> dict[str, Any]:
    intent = deepcopy(current) if isinstance(current, dict) else {}
    intent["turn_mode"] = "respond"
    if route == "supermarket_encounter":
        intent["primary_intention"] = "brief_first_contact_response"
    elif route in _SUPERMARKET_ROUTES:
        intent["primary_intention"] = "follow_supermarket_screenplay_block"
    else:
        intent["primary_intention"] = "follow_current_screenplay_block"
    return intent


def _idle_sexual_state(current: Any) -> dict[str, Any]:
    state = deepcopy(current) if isinstance(current, dict) else {}
    state.update(
        {
            "scene_phase": "idle",
            "arousal_level": 0.0,
            "stimulation_turns": 0,
            "mary_pre_orgasm": False,
            "mary_orgasm_allowed": False,
            "mary_orgasm_done": False,
            "user_orgasm_pending": False,
            "user_orgasm_done": False,
            "aftercare_required": False,
        }
    )
    return state


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(original, "_mary_casada_inputs_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        scenario_id, route = _scenario_context()
        if scenario_id != SCENARIO_ID:
            return str(original(*args, **kwargs) or "")

        aligned = dict(kwargs)
        aligned["include_voice_examples"] = False
        aligned["turn_direction"] = _aligned_direction(route, aligned.get("turn_direction"))
        aligned["turn_intent"] = _aligned_intent(route, aligned.get("turn_intent"))
        if route in _SUPERMARKET_ROUTES:
            aligned["sexual_state"] = _idle_sexual_state(aligned.get("sexual_state"))
        return str(original(*args, **aligned) or "")

    wrapper._mary_casada_inputs_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def aplicar_entradas_prompt_casada_frustrada() -> None:
    module = sys.modules.get("__main__")
    if module is not None:
        _patch_prompt_builder(module)


def install_casada_frustrada_prompt_inputs() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_entradas_prompt_casada_frustrada()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_PROMPT_INPUTS_VERSION",
    "aplicar_entradas_prompt_casada_frustrada",
    "install_casada_frustrada_prompt_inputs",
]
