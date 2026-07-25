from __future__ import annotations

import re
import sys
from copy import deepcopy
from functools import wraps
from typing import Any, Callable

import streamlit as st

from scenarios.stories.casada_frustrada.screenplay import SCENARIO_ID


CASADA_FRUSTRADA_PHONE_RECOVERY_VERSION = (
    "casada-frustrada-phone-recovery-v1-contextual-farewell"
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None

_USER_ACCEPTS_FAREWELL = (
    r"\ba gente se esbarra\b",
    r"\ba gente se v[eê]\b",
    r"\bobrigad[oa] pela ajuda\b",
    r"\bvaleu pela ajuda\b",
    r"\bpode ser\b",
    r"\bat[eé] mais\b",
    r"\btchau\b",
)

_MARY_STARTS_FAREWELL = (
    r"\bvou (?:continuar|terminar|acabar) (?:as|minhas) compras\b",
    r"\bantes que eu esqueça metade da lista\b",
    r"\ba gente se v[eê] por a[ií]\b",
    r"\ba gente se esbarra\b",
    r"\bvou indo\b",
    r"\btchauzinho\b",
    r"\bat[eé] mais\b",
)

_PERSONAL_CONVERSATION_MARKERS = (
    "meu nome é",
    "me chamo",
    "sou janio",
    "plaza",
    "bloco b",
    "vizinho",
    "vizinha",
    "moro no",
    "vinho",
    "cabernet",
)

_EXPLICIT_REFUSAL = (
    r"\bn[aã]o quero\b",
    r"\bmelhor n[aã]o\b",
    r"\bn[aã]o tenho interesse\b",
    r"\bme deixa\b",
    r"\bpare\b",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = _text(text).lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def _scenario_instance() -> dict[str, Any] | None:
    instance = st.session_state.get("scenario_instance")
    return instance if isinstance(instance, dict) else None


def _collect_messages(kwargs: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "recent_messages",
        "messages",
        "history",
        "conversation_history",
    ):
        value = kwargs.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    for key in ("mensagens", "chat_messages", "historico_mensagens"):
        value = st.session_state.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _message_text(item: dict[str, Any]) -> str:
    return _text(item.get("content") or item.get("text"))


def _latest_by_role(
    messages: list[dict[str, Any]],
    role: str,
) -> str:
    for item in reversed(messages):
        if _text(item.get("role")).lower() == role:
            text = _message_text(item)
            if text:
                return text
    return ""


def _latest_user_text(
    kwargs: dict[str, Any],
    messages: list[dict[str, Any]],
) -> str:
    for key in (
        "user_text",
        "user_message",
        "fala_usuario",
        "last_user_message",
    ):
        text = _text(kwargs.get(key))
        if text:
            return text
    return _latest_by_role(messages, "user")


def _conversation_matured(
    instance: dict[str, Any],
    messages: list[dict[str, Any]],
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
        _message_text(item).lower()
        for item in messages[-16:]
    )
    has_personal_content = any(
        marker in recent_text
        for marker in _PERSONAL_CONVERSATION_MARKERS
    )
    return interaction_count >= 4 and has_personal_content


def _contextual_farewell_detected(
    *,
    user_text: str,
    messages: list[dict[str, Any]],
) -> bool:
    if _matches_any(user_text, _EXPLICIT_REFUSAL):
        return False

    user_accepts = _matches_any(user_text, _USER_ACCEPTS_FAREWELL)
    if not user_accepts:
        return False

    previous_assistant = ""
    found_current_user = False
    for item in reversed(messages):
        role = _text(item.get("role")).lower()
        text = _message_text(item)
        if role == "user" and not found_current_user:
            found_current_user = True
            continue
        if role == "assistant":
            previous_assistant = text
            break

    if not previous_assistant:
        previous_assistant = _latest_by_role(messages[:-1], "assistant")

    return _matches_any(previous_assistant, _MARY_STARTS_FAREWELL)


def _activate_phone_exchange(kwargs: dict[str, Any]) -> bool:
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

    messages = _collect_messages(kwargs)
    user_text = _latest_user_text(kwargs, messages)
    if not _contextual_farewell_detected(
        user_text=user_text,
        messages=messages,
    ):
        return False
    if not _conversation_matured(instance, messages):
        return False

    focus = (
        "Mary percebe que a despedida vai encerrar de verdade o encontro. Ela "
        "quase aceita e vai embora, mas trava por um instante: é casada e sente "
        "vergonha de pedir o número de outro homem. Depois desse conflito visível "
        "na fala, pede o contato de forma curta, insegura e fácil de recusar. Não "
        "faça piada, não disfarce como favor prático e não diga apenas tchau."
    )

    for target in (instance, scene_state):
        target["current_route"] = "phone_exchange"
        target["current_beat"] = "hesitation_before_phone_request"
        target["current_phase"] = "familiarity"
        target["ending_ready"] = False
        target["ending_sent"] = False
        target["ending_forced"] = False
        target["ending_signal"] = False
        target["ending_reason"] = ""
        target["ending_type"] = ""
        target["user_disengaged"] = False

    scene_state["scene_closing_signal"] = True
    scene_state["phone_request_due"] = True
    scene_state["recommended_focus"] = focus
    scene_state["last_action_choice"] = "advance"
    scene_state["last_mary_initiative_strength"] = 2

    last_analysis = scene_state.get("last_director_analysis")
    if isinstance(last_analysis, dict):
        last_analysis.update(
            {
                "recommended_route": "phone_exchange",
                "recommended_beat": "hesitation_before_phone_request",
                "scene_closing_signal": True,
                "ending_signal": False,
                "user_disengaged": False,
                "recommended_phase": "familiarity",
                "action_choice": "advance",
                "mary_initiative_strength": 2,
                "should_create_hook": True,
                "mary_should_add_affordance": True,
                "recommended_focus": focus,
            }
        )
    return True


def _force_phone_direction(current: Any) -> dict[str, Any]:
    direction = deepcopy(current) if isinstance(current, dict) else {}
    direction.update(
        {
            "experience_mode": "natural_conversation",
            "primary_intention": "hesitate_then_request_phone_now",
            "emotional_color": "married_embarrassed_conflicted_and_hopeful",
            "voice_register": "natural",
            "should_lead": True,
            "should_reveal": False,
            "should_create_hook": True,
            "mary_should_add_affordance": True,
            "avoid_question": False,
            "response_scope": "brief",
            "reason": (
                _text(direction.get("reason"))
                + ";casada_frustrada:contextual_farewell_phone_request"
            ).strip(";"),
        }
    )
    return direction


def _force_phone_intent(current: Any) -> dict[str, Any]:
    intent = deepcopy(current) if isinstance(current, dict) else {}
    intent["turn_mode"] = "respond"
    intent["primary_intention"] = "hesitate_then_request_phone_now"
    return intent


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(
        original,
        "_mary_phone_recovery_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        activated = _activate_phone_exchange(dict(kwargs))
        if not activated:
            return str(original(*args, **kwargs) or "")

        aligned = dict(kwargs)
        aligned["turn_direction"] = _force_phone_direction(
            aligned.get("turn_direction")
        )
        aligned["turn_intent"] = _force_phone_intent(
            aligned.get("turn_intent")
        )
        return str(original(*args, **aligned) or "")

    wrapper._mary_phone_recovery_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def aplicar_recuperacao_telefone_casada_frustrada() -> None:
    module = sys.modules.get("__main__")
    if module is not None:
        _patch_prompt_builder(module)


def install_casada_frustrada_phone_recovery() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_recuperacao_telefone_casada_frustrada()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_PHONE_RECOVERY_VERSION",
    "aplicar_recuperacao_telefone_casada_frustrada",
    "install_casada_frustrada_phone_recovery",
]
