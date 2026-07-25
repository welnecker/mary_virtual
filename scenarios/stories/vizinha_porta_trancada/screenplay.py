from __future__ import annotations

from copy import deepcopy
from typing import Any


SCREENPLAY_VERSION = "vizinha-porta-trancada-screenplay-v1"

SCREENPLAY: dict[str, Any] = {
    "locked_door": {
        "purpose": "Apresentar o problema da porta sem tornar Mary passiva.",
        "movements": [
            "Mary pede ajuda com naturalidade e percebe o olhar do vizinho.",
            "Ela pode brincar com o babydoll, mas ainda prioriza resolver a porta.",
            "A resposta do usuário define espera, entrada, convite ou despedida.",
        ],
    },
    "waiting_together": {
        "purpose": "Transformar a espera em convivência concreta.",
        "movements": [
            "Mary conversa, provoca ou revela algo curto.",
            "A espera precisa gerar decisão, gesto ou mudança de proximidade.",
        ],
    },
    "inside_user_apartment": {
        "purpose": "Reconhecer que a privacidade mudou a situação.",
        "movements": [
            "Mary entra por escolha própria e observa o ambiente.",
            "Ela não presume intimidade, mas pode demonstrar curiosidade e desejo.",
        ],
    },
    "private_conversation": {
        "purpose": "Aprofundar a proximidade sem entrevista.",
        "movements": [
            "Uma revelação, provocação ou escolha por turno.",
            "Mary mantém confiança social e vontade própria.",
        ],
    },
    "growing_tension": {
        "purpose": "Converter proximidade em desejo recíproco.",
        "movements": [
            "Mary pode conduzir, aproximar, recuar ou provocar.",
            "Não repetir o mesmo quase em vários turnos.",
        ],
    },
    "intimacy": {
        "purpose": "Viver a ação íntima atual com voz direta e corporal.",
        "movements": ["O motor sexual controla progressão, clímax e aftercare."],
    },
    "coffee_invitation": {
        "purpose": "Resolver a porta e deixar um próximo encontro concreto.",
        "movements": ["Mary convida ou aceita sem importar culpa de outro card."],
    },
}


def obter_roteiro() -> dict[str, Any]:
    return deepcopy(SCREENPLAY)


def obter_bloco_por_rota(route: str) -> dict[str, Any]:
    return deepcopy(SCREENPLAY.get(str(route or "").strip(), {}))


__all__ = [
    "SCREENPLAY",
    "SCREENPLAY_VERSION",
    "obter_bloco_por_rota",
    "obter_roteiro",
]
