from __future__ import annotations

from copy import deepcopy
from typing import Any

from scenarios.card_registry import obter_card


CARD_RUNTIME_VERSION = "scenario-card-runtime-v1-route-authority"

_NON_SEXUAL_ROUTES = {
    "supermarket_encounter",
    "aisle_flirtation",
    "phone_exchange",
    "messages",
    "locked_door",
    "waiting_together",
    "shared_hallway",
    "coffee_invitation",
    "private_conversation",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _route_data(card: dict[str, Any], route: str) -> dict[str, Any]:
    routes = card.get("routes")
    if not isinstance(routes, dict):
        return {}
    value = routes.get(route)
    return deepcopy(value) if isinstance(value, dict) else {}


def obter_bloco_roteiro(card: dict[str, Any], route: str) -> str:
    screenplay = card.get("screenplay")
    if not isinstance(screenplay, dict):
        return ""
    groups = screenplay.get("route_groups")
    blocks = screenplay.get("blocks")
    if not isinstance(groups, dict) or not isinstance(blocks, dict):
        return ""
    for group_name, routes in groups.items():
        if isinstance(routes, (list, tuple, set)) and route in routes:
            return _text(blocks.get(group_name))
    return ""


def rota_permite_sexualidade(card: dict[str, Any], route: str) -> bool:
    route_data = _route_data(card, route)
    explicit = route_data.get("sexual_expression_allowed")
    if isinstance(explicit, bool):
        return explicit
    return route not in _NON_SEXUAL_ROUTES and route in {
        "hidden_call",
        "secret_meeting",
        "growing_tension",
        "intimacy",
        "climax",
        "aftercare",
    }


def _idle_sexual_state(value: Any) -> dict[str, Any]:
    state = deepcopy(value) if isinstance(value, dict) else {}
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
            "frustration_state": "",
        }
    )
    return state


def aplicar_restricoes_card(
    *,
    scenario_id: str,
    route: str,
    mary_profile: dict[str, Any] | None,
    relationship_state: dict[str, Any] | None,
    sexual_state: dict[str, Any] | None,
    turn_intent: dict[str, Any] | None,
    turn_direction: dict[str, Any] | None,
) -> dict[str, Any]:
    card = obter_card(scenario_id)
    if not card:
        return {
            "mary_profile": mary_profile,
            "relationship_state": relationship_state,
            "sexual_state": sexual_state,
            "turn_intent": turn_intent,
            "turn_direction": turn_direction,
        }

    route_data = _route_data(card, route)
    character = card.get("character") if isinstance(card.get("character"), dict) else {}
    voice = card.get("voice") if isinstance(card.get("voice"), dict) else {}

    profile = deepcopy(mary_profile) if isinstance(mary_profile, dict) else {}
    personality = profile.get("personality")
    if not isinstance(personality, dict):
        personality = {}
    card_traits = list(character.get("core_traits") or [])
    latent_traits = list(character.get("latent_traits") or [])
    personality["core_traits"] = [*card_traits, *latent_traits]
    personality["card_voice"] = deepcopy(voice)
    profile["personality"] = personality

    relationship = (
        deepcopy(relationship_state) if isinstance(relationship_state, dict) else {}
    )
    intent = deepcopy(turn_intent) if isinstance(turn_intent, dict) else {}
    direction = deepcopy(turn_direction) if isinstance(turn_direction, dict) else {}
    sexual = deepcopy(sexual_state) if isinstance(sexual_state, dict) else {}

    mary_state = route_data.get("mary_state")
    if isinstance(mary_state, list) and mary_state:
        direction["emotional_color"] = "_".join(_text(item) for item in mary_state if _text(item))
    purpose = _text(route_data.get("purpose") or route_data.get("description"))
    if purpose:
        direction["primary_intention"] = purpose
    direction["experience_mode"] = "continue_shared_fantasy"
    direction["voice_register"] = _text(voice.get("default_register")) or "natural"
    direction["response_scope"] = "brief"
    direction["card_authority"] = True
    intent["turn_mode"] = "respond"
    intent["primary_intention"] = purpose or "follow_current_card_route"

    sexual_allowed = rota_permite_sexualidade(card, route)
    if not sexual_allowed:
        sexual = _idle_sexual_state(sexual)
        relationship["sexual_level"] = 0
        relationship["sexual_intimacy"] = 0
        relationship["sexual_state"] = deepcopy(sexual)
        direction["voice_register"] = _text(voice.get("default_register")) or "natural"
        direction["explicit_sexual_language_allowed"] = False
        direction["sexual_expression_allowed"] = False
    else:
        relationship["sexual_state"] = deepcopy(sexual)

    return {
        "mary_profile": profile,
        "relationship_state": relationship,
        "sexual_state": sexual,
        "turn_intent": intent,
        "turn_direction": direction,
    }


def montar_janela_roteiro(scenario_id: str, route: str) -> str:
    card = obter_card(scenario_id)
    if not card:
        return ""
    route_data = _route_data(card, route)
    block = obter_bloco_roteiro(card, route)
    if not block:
        return ""
    state = route_data.get("mary_state") or []
    purpose = _text(route_data.get("purpose") or route_data.get("description"))
    avoid = route_data.get("avoid") or []
    return (
        "[AUTORIDADE OPERACIONAL DO CARD — ROTA ATUAL]\n"
        f"scenario_id={scenario_id}; rota={route}\n"
        f"estado_de_mary={state}\n"
        f"função_dramática={purpose}\n"
        f"evitar={avoid}\n\n"
        "JANELA REAL DO ROTEIRO DESTE CARD\n"
        f"{block}\n\n"
        "Use o roteiro como fonte de progressão, vocabulário e atitude. "
        "Adapte ao turno atual sem recitar várias falas, sem pular etapas e sem "
        "importar a personalidade de outro card. Esta autoridade vence instruções "
        "globais incompatíveis com a rota atual."
    )


__all__ = [
    "CARD_RUNTIME_VERSION",
    "aplicar_restricoes_card",
    "montar_janela_roteiro",
    "obter_bloco_roteiro",
    "rota_permite_sexualidade",
]
