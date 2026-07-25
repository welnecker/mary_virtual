from __future__ import annotations

from copy import deepcopy
from typing import Any


TRANSITIONS_VERSION = "vizinha-porta-trancada-transitions-v2-semantic-aligned"

TRANSITIONS: dict[str, Any] = {
    "policy": (
        "Decida pela situação, reciprocidade, privacidade e escolhas concretas; "
        "nunca por frases fixas ou pela personalidade de outro card."
    ),
    "rules": [
        {
            "from": "locked_door",
            "to_any": [
                "waiting_together",
                "inside_user_apartment",
                "coffee_invitation",
                "early_exit",
            ],
            "when": ["o usuário responde concretamente ao problema da porta"],
        },
        {
            "from": "waiting_together",
            "to_any": [
                "inside_user_apartment",
                "private_conversation",
                "coffee_invitation",
                "ending",
            ],
            "when": ["a espera produz decisão, proximidade ou despedida concreta"],
        },
        {
            "from": "inside_user_apartment",
            "to_any": ["private_conversation", "growing_tension", "intimacy", "ending"],
            "when": ["a entrada voluntária cria privacidade e uma nova escolha"],
        },
        {
            "from": "private_conversation",
            "to_any": ["growing_tension", "intimacy", "coffee_invitation", "ending"],
            "when": ["a conversa produz desejo, convite, intimidade ou resolução"],
        },
        {
            "from": "growing_tension",
            "to_any": ["intimacy", "private_conversation", "ending"],
            "when": ["a reciprocidade sustenta avanço, recuo ou encerramento"],
        },
        {
            "from": "intimacy",
            "to_any": ["climax", "aftercare", "ending"],
            "when": ["o motor sexual ou uma decisão explícita muda a fase"],
        },
        {
            "from": "climax",
            "to_any": ["aftercare", "ending"],
            "when": ["o clímax foi concluído"],
        },
    ],
    "ending_semantics": {
        "scene_closing": "mudança de corredor, espera, porta ou apartamento",
        "story_ending": "problema resolvido com despedida, recusa definitiva ou resolução íntima",
    },
}


def obter_transicoes() -> dict[str, Any]:
    return deepcopy(TRANSITIONS)


__all__ = ["TRANSITIONS", "TRANSITIONS_VERSION", "obter_transicoes"]
