from __future__ import annotations

from copy import deepcopy
from typing import Any

from .story_state import normalizar_estado_narrativo


PROMPT_CONTEXT_VERSION = "casada-frustrada-prompt-context-v1"


def aplicar_estado_narrativo_ao_compasso(
    compass_value: Any,
    story_state_value: Any,
) -> dict[str, Any]:
    compass = deepcopy(compass_value) if isinstance(compass_value, dict) else {}
    story_state = normalizar_estado_narrativo(story_state_value)

    blocked = set(story_state.get("blocked_movements") or [])
    movements = list(compass.get("possible_movements") or [])

    filtered_movements: list[str] = []
    for movement in movements:
        text = str(movement or "").strip()
        normalized = text.casefold()
        if not text:
            continue
        if (
            "ask_phone_number" in blocked
            or "offer_phone_number_again" in blocked
        ) and any(marker in normalized for marker in ("telefone", "número", "numero", "contato")):
            continue
        filtered_movements.append(text)

    compass["possible_movements"] = filtered_movements
    compass["story_reality"] = {
        "version": PROMPT_CONTEXT_VERSION,
        "confirmed_facts": list(story_state.get("confirmed_facts") or [])[-12:],
        "active_tensions": list(story_state.get("active_tensions") or [])[-8:],
        "completed_functions": list(story_state.get("completed_functions") or [])[-12:],
        "blocked_movements": list(story_state.get("blocked_movements") or [])[-12:],
        "authority": (
            "Estes fatos descrevem a realidade já estabelecida da sessão e têm prioridade "
            "sobre sugestões, exemplos e referências diagnósticas do roteiro."
        ),
    }

    if "establish_contact_channel" in set(
        story_state.get("completed_functions") or []
    ):
        compass["interpretation_rules"] = list(dict.fromkeys([
            *list(compass.get("interpretation_rules") or []),
            "O canal de contato já foi estabelecido; não pedir nem oferecer telefone novamente.",
            "Interpretar a conversa a partir do vínculo já existente e seguir para a função dramática ainda aberta.",
        ]))

    return compass


__all__ = [
    "PROMPT_CONTEXT_VERSION",
    "aplicar_estado_narrativo_ao_compasso",
]
