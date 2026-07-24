from __future__ import annotations

import re
import sys
from copy import deepcopy
from functools import wraps
from typing import Any, Callable

import streamlit as st

from scenarios.stories.casada_frustrada.screenplay import SCENARIO_ID


CASADA_FRUSTRADA_PROMPT_INPUTS_VERSION = (
    "casada-frustrada-prompt-inputs-v2-hesitant-phone-at-closing"
)

_SUPERMARKET_ROUTES = {
    "supermarket_encounter",
    "aisle_flirtation",
    "phone_exchange",
}

_CLOSING_PATTERNS = (
    r"\b(vou|preciso|tenho que) (?:terminar|continuar|acabar) (?:as|minhas) compras\b",
    r"\b(vou|preciso|tenho que) ir\b",
    r"\b(vou indo|t[oô] indo|at[eé] mais|a gente se v[eê])\b",
    r"\bterminar minhas compras\b",
    r"\bseguir com minhas compras\b",
)

_CONVERSATION_MARKERS = (
    "meu nome é",
    "me chamo",
    "sou janio",
    "plaza",
    "bloco b",
    "vizinho",
    "vizinha",
    "moro no",
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _scenario_instance() -> dict[str, Any] | None:
    instance = st.session_state.get("scenario_instance")
    return instance if isinstance(instance, dict) else None


def _scenario_context() -> tuple[str, str]:
    instance = _scenario_instance()
    if not isinstance(instance, dict):
        return "", ""
    scene_state = instance.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}
    scenario_id = _text(instance.get("scenario_id"))
    route = _text(
        instance.get("current_route")
        or scene_state.get("current_route")
    )
    return scenario_id, route


def _collect_recent_messages(kwargs: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "recent_messages",
        "messages",
        "history",
        "conversation_history",
    ):
        value = kwargs.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    for key in (
        "mensagens",
        "chat_messages",
        "historico_mensagens",
    ):
        value = st.session_state.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _latest_user_text(
    kwargs: dict[str, Any],
    recent_messages: list[dict[str, Any]],
) -> str:
    for key in (
        "user_text",
        "user_message",
        "fala_usuario",
        "last_user_message",
    ):
        value = _text(kwargs.get(key))
        if value:
            return value

    for item in reversed(recent_messages):
        if _text(item.get("role")).lower() != "user":
            continue
        content = _text(item.get("content") or item.get("text"))
        if content:
            return content
    return ""


def _has_closing_signal(text: str) -> bool:
    lowered = _text(text).lower()
    return any(re.search(pattern, lowered) for pattern in _CLOSING_PATTERNS)


def _has_explicit_refusal(text: str) -> bool:
    lowered = _text(text).lower()
    patterns = (
        r"\bn[aã]o quero\b",
        r"\bmelhor n[aã]o\b",
        r"\bn[aã]o tenho interesse\b",
        r"\bme deixa\b",
        r"\bpare\b",
    )
    return any(re.search(pattern, lowered) for pattern in patterns)


def _conversation_matured(
    instance: dict[str, Any],
    recent_messages: list[dict[str, Any]],
) -> bool:
    scene_state = instance.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}

    interaction_count = 0
    for value in (
        instance.get("interaction_count"),
        scene_state.get("interaction_number"),
        scene_state.get("interaction_count"),
    ):
        try:
            interaction_count = max(interaction_count, int(value or 0))
        except (TypeError, ValueError):
            pass

    recent_text = " ".join(
        _text(item.get("content") or item.get("text")).lower()
        for item in recent_messages[-12:]
    )
    concrete_bond = any(
        marker in recent_text
        for marker in _CONVERSATION_MARKERS
    )

    # Não basta haver uma despedida. Mary só considera pedir o contato quando
    # já houve conversa pessoal concreta: nomes, vizinhança, prédio ou rotina.
    return interaction_count >= 4 and concrete_bond


def _prepare_hesitant_phone_exchange(kwargs: dict[str, Any]) -> bool:
    instance = _scenario_instance()
    if not isinstance(instance, dict):
        return False
    if _text(instance.get("scenario_id")) != SCENARIO_ID:
        return False

    scene_state = instance.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}
        instance["scene_state"] = scene_state

    route = _text(
        instance.get("current_route")
        or scene_state.get("current_route")
    )
    if route not in {"supermarket_encounter", "aisle_flirtation"}:
        return False
    if bool(scene_state.get("phone_numbers_exchanged")):
        return False

    recent_messages = _collect_recent_messages(kwargs)
    user_text = _latest_user_text(kwargs, recent_messages)
    if not _has_closing_signal(user_text):
        return False
    if _has_explicit_refusal(user_text):
        return False
    if not _conversation_matured(instance, recent_messages):
        return False

    # A despedida encerra apenas o encontro físico. Ela não encerra a história.
    # Neste ponto Mary percebe que pode perder o contato. Como é casada, pedir o
    # número não é natural nem fácil: há vergonha, conflito e quase desistência.
    instance["current_route"] = "phone_exchange"
    instance["current_beat"] = "closing_sign_detected"
    instance["current_phase"] = "familiarity"
    instance["ending_ready"] = False
    instance["ending_sent"] = False
    instance["ending_reason"] = ""
    instance["ending_type"] = ""

    scene_state["current_route"] = "phone_exchange"
    scene_state["current_beat"] = "closing_sign_detected"
    scene_state["current_phase"] = "familiarity"
    scene_state["ending_ready"] = False
    scene_state["ending_sent"] = False
    scene_state["ending_reason"] = ""
    scene_state["ending_type"] = ""
    scene_state["user_disengaged"] = False
    scene_state["scene_closing_signal"] = True
    scene_state["recommended_focus"] = (
        "A despedida ficou real. Mary quase deixa o encontro acabar, porque pedir "
        "o número de outro homem a constrange por ser casada. Só depois dessa "
        "hesitação ela cria coragem para pedir de forma curta, insegura e sem pressão."
    )
    scene_state["last_action_choice"] = "advance"
    scene_state["last_mary_initiative_strength"] = 2

    last_analysis = scene_state.get("last_director_analysis")
    if isinstance(last_analysis, dict):
        last_analysis["recommended_route"] = "phone_exchange"
        last_analysis["recommended_beat"] = "closing_sign_detected"
        last_analysis["scene_closing_signal"] = True
        last_analysis["ending_signal"] = False
        last_analysis["user_disengaged"] = False
        last_analysis["recommended_phase"] = "familiarity"
        last_analysis["action_choice"] = "advance"
        last_analysis["mary_initiative_strength"] = 2
        last_analysis["recommended_focus"] = scene_state["recommended_focus"]

    return True


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
                "primary_intention": "hesitantly_request_phone_at_real_farewell",
                "emotional_color": "married_embarrassed_conflicted_and_hopeful",
                "should_lead": True,
                "should_reveal": False,
                "avoid_question": False,
                "response_scope": "brief",
                "reason": (
                    _text(direction.get("reason"))
                    + ";casada_frustrada:hesitant_phone_request"
                ).strip(";"),
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
    elif route == "phone_exchange":
        intent["primary_intention"] = (
            "ask_phone_only_after_hesitation_at_real_farewell"
        )
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
        scenario_id, _ = _scenario_context()
        if scenario_id != SCENARIO_ID:
            return str(original(*args, **kwargs) or "")

        # Corrige somente a despedida madura no supermercado. Fora dessa condição,
        # a rota e a liberdade do diretor permanecem intactas.
        _prepare_hesitant_phone_exchange(dict(kwargs))
        _, route = _scenario_context()

        aligned = dict(kwargs)
        aligned["include_voice_examples"] = False
        aligned["turn_direction"] = _aligned_direction(
            route,
            aligned.get("turn_direction"),
        )
        aligned["turn_intent"] = _aligned_intent(
            route,
            aligned.get("turn_intent"),
        )
        if route in _SUPERMARKET_ROUTES:
            aligned["sexual_state"] = _idle_sexual_state(
                aligned.get("sexual_state")
            )
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
