from __future__ import annotations

from copy import deepcopy
from typing import Any


ROUTES_VERSION = "vizinha-routes-v2-responsive"

ROUTES: dict[str, Any] = {
    "locked_door": {
        "description": "Mary apresenta o problema da porta e reage à escolha concreta do vizinho.",
        "possible_next_routes": [
            "waiting_together",
            "inside_user_apartment",
            "coffee_invitation",
            "early_exit",
        ],
        "avoid": "Não repetir indefinidamente o pedido de ajuda ou o constrangimento do babydoll.",
    },
    "waiting_together": {
        "description": "Os dois permanecem juntos enquanto resolvem a situação, com espaço para humor, provocação ou recuo.",
        "possible_next_routes": [
            "inside_user_apartment",
            "private_conversation",
            "coffee_invitation",
            "ending",
        ],
        "avoid": "Não transformar a espera em entrevista ou conversa sem consequência.",
    },
    "inside_user_apartment": {
        "description": "Mary aceita entrar no apartamento do usuário e a privacidade muda concretamente a dinâmica.",
        "possible_next_routes": [
            "private_conversation",
            "growing_tension",
            "intimacy",
            "ending",
        ],
        "scene_updates": {
            "private_space": True,
            "privacy_established": True,
            "mary_inside_apartment": False,
            "user_inside_apartment": True,
        },
    },
    "private_conversation": {
        "description": "Mary e o usuário conversam em privacidade, mas cada turno precisa produzir revelação, decisão ou gesto.",
        "possible_next_routes": [
            "growing_tension",
            "intimacy",
            "coffee_invitation",
            "ending",
        ],
    },
    "growing_tension": {
        "description": "A atração fica evidente e Mary pode conduzir, provocar, pedir, recuar ou avançar conforme a reciprocidade.",
        "possible_next_routes": [
            "intimacy",
            "private_conversation",
            "ending",
        ],
        "avoid": "Não manter vários turnos apenas no quase ou na mesma provocação.",
    },
    "intimacy": {
        "description": "A intimidade está ativa; o motor sexual governa continuidade, limites, prazer e resolução.",
        "possible_next_routes": [
            "climax",
            "aftercare",
            "ending",
        ],
        "avoid": "Não criar micropassos nem exigir comando do usuário para cada gesto de Mary.",
    },
    "climax": {
        "description": "A tensão principal alcança resolução corporal ou narrativa clara.",
        "possible_next_routes": ["aftercare", "ending"],
        "avoid": "Não prolongar artificialmente o pré-clímax depois que a resolução estiver pronta.",
    },
    "aftercare": {
        "description": "Mary permanece presente, sensual e humana depois da resolução, sem desligamento abrupto.",
        "possible_next_routes": ["ending", "private_conversation"],
    },
    "coffee_invitation": {
        "description": "Mary resolve a situação imediata e transforma o encontro num gancho concreto para outro contato.",
        "possible_next_routes": ["ending"],
    },
    "ending": {
        "description": "Mary encerra a experiência de modo curto, coerente e memorável, sem abrir outro arco dentro da mesma história.",
        "possible_next_routes": [],
    },
    "early_exit": {
        "description": "O usuário encerra ou recusa a situação; Mary respeita e finaliza sem insistência ou punição.",
        "possible_next_routes": [],
    },
}


def obter_rotas() -> dict[str, Any]:
    return deepcopy(ROUTES)


__all__ = ["ROUTES_VERSION", "ROUTES", "obter_rotas"]
