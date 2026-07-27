from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any

from .story_state import (
    adicionar_fatos,
    bloquear_movimentos,
    concluir_funcoes,
    normalizar_estado_narrativo,
)


STORY_OBSERVER_VERSION = "casada-frustrada-story-observer-v1"

CONTACT_FUNCTION = "establish_contact_channel"
ASK_PHONE_MOVEMENT = "ask_phone_number"
OFFER_PHONE_MOVEMENT = "offer_phone_number_again"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _conversation_text(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in messages[-16:]:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("role"))
        content = _text(item.get("content"))
        if role in {"user", "assistant"} and content:
            parts.append(_normalize(content))
    return " ".join(parts)


def _contact_channel_established(
    *,
    route: str,
    beat_id: str,
    conversation: str,
) -> bool:
    if route in {"messages", "hidden_call", "secret_meeting_plan", "secret_meeting"}:
        return True
    if beat_id in {
        "home_first_message",
        "seek_bathroom_privacy",
        "admit_neediness",
        "admit_attraction",
        "offer_video",
    }:
        return True
    markers = (
        "ja estamos conversando por mensagens",
        "a gente ja esta conversando por mensagens",
        "a gente ta conversando por mensagens",
        "estamos falando por aqui",
        "continuar por aqui",
        "nesse chat",
        "por mensagem",
        "pelo celular",
    )
    return any(marker in conversation for marker in markers)


def _user_requested_slowdown(conversation: str) -> bool:
    markers = (
        "calma mary",
        "vai com calma",
        "nao vai com tanta sede",
        "muito rapido",
        "pode fugir do controle",
        "talvez nao seja uma boa ideia",
    )
    return any(marker in conversation for marker in markers)


def observar_estado_narrativo(
    state_value: Any,
    *,
    messages: list[dict[str, Any]],
    route: str,
    beat_id: str,
) -> dict[str, Any]:
    state = normalizar_estado_narrativo(state_value)
    conversation = _conversation_text(messages)
    observation: dict[str, Any] = {
        "version": STORY_OBSERVER_VERSION,
        "route": _text(route),
        "beat": _text(beat_id),
        "new_facts": [],
        "completed_functions": [],
        "blocked_movements": [],
    }

    if _contact_channel_established(
        route=_text(route),
        beat_id=_text(beat_id),
        conversation=conversation,
    ):
        facts = (
            "o canal de comunicação por mensagens já está estabelecido",
            "Mary e o usuário já conseguem conversar diretamente",
        )
        adicionar_fatos(state, *facts)
        concluir_funcoes(state, CONTACT_FUNCTION)
        bloquear_movimentos(state, ASK_PHONE_MOVEMENT, OFFER_PHONE_MOVEMENT)
        observation["new_facts"].extend(facts)
        observation["completed_functions"].append(CONTACT_FUNCTION)
        observation["blocked_movements"].extend(
            [ASK_PHONE_MOVEMENT, OFFER_PHONE_MOVEMENT]
        )

    if _user_requested_slowdown(conversation):
        tension = "o usuário teme que Mary acelere e que a situação fuja do controle"
        state["active_tensions"] = list(dict.fromkeys([
            *state.get("active_tensions", []),
            tension,
        ]))
        observation.setdefault("active_tensions", []).append(tension)

    state["current_scene"] = _text(route) or state.get("current_scene", "")
    state["last_observation"] = deepcopy(observation)
    return state


__all__ = [
    "STORY_OBSERVER_VERSION",
    "CONTACT_FUNCTION",
    "ASK_PHONE_MOVEMENT",
    "OFFER_PHONE_MOVEMENT",
    "observar_estado_narrativo",
]
