from __future__ import annotations

from copy import deepcopy
from typing import Any


TRANSITIONS_VERSION = "vizinha-porta-trancada-transitions-v1-semantic"

TRANSITIONS: dict[str, Any] = {
    "policy": (
        "Decida pela situação, reciprocidade, privacidade e escolhas concretas; "
        "nunca por frases fixas ou pela personalidade de outro card."
    ),
    "rules": [
        {
            "from": "locked_door",
            "to": "shared_hallway",
            "when": ["o usuário responde ao problema da porta e permanece presente"],
        },
        {
            "from": "shared_hallway",
            "to": "private_space",
            "when": [
                "a porta foi resolvida ou surgiu alternativa concreta",
                "há convite ou entrada voluntária em espaço privado",
            ],
        },
        {
            "from": "private_space",
            "to": "tension",
            "when": ["a proximidade deixa de ser apenas prática e ganha desejo recíproco"],
        },
        {
            "from": "tension",
            "to": "intimacy",
            "when": ["a intimidade física começa com reciprocidade"],
        },
        {
            "from": "intimacy",
            "to": "climax",
            "when": ["o motor sexual confirma proximidade ou início do clímax"],
        },
        {
            "from": "climax",
            "to": "aftercare",
            "when": ["o clímax foi concluído"],
        },
    ],
    "ending_semantics": {
        "scene_closing": "mudança de corredor, porta ou apartamento",
        "story_ending": "problema resolvido com despedida, recusa definitiva ou resolução íntima",
    },
}


def obter_transicoes() -> dict[str, Any]:
    return deepcopy(TRANSITIONS)


__all__ = ["TRANSITIONS", "TRANSITIONS_VERSION", "obter_transicoes"]
