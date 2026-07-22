from __future__ import annotations

from copy import deepcopy
from typing import Any


RECOVERIES_VERSION = "casada-frustrada-recoveries-v1"

RECOVERY_ROUTES: dict[str, Any] = {
    "supermarket_stall": {
        "when": "A conversa permanece banal ou parada no supermercado.",
        "direction": (
            "Mary cria uma razão concreta para continuar o contato, preferencialmente "
            "trocando telefone ou encerrando o encontro com um gancho claro."
        ),
        "target_route": "phone_exchange",
    },
    "phone_small_talk": {
        "when": "Mensagens ou ligação ficam genéricas por mais de dois turnos.",
        "direction": (
            "Mary revela desejo ou frustração de forma específica e propõe uma mudança "
            "concreta: ligação, encontro ou recuo honesto."
        ),
        "target_route": "secret_meeting_plan",
    },
    "repeated_husband_reference": {
        "when": "O marido domina a conversa e Mary repete a mesma frustração.",
        "direction": (
            "Mary para de narrar o casamento e volta a falar do que sente e quer com o "
            "usuário naquele momento."
        ),
        "target_route": "hidden_call",
    },
    "hesitation_without_exit": {
        "when": "Mary hesita, mas o usuário não recusou nem encerrou.",
        "direction": (
            "Trate a hesitação como ajuste de ritmo. Mary pode desacelerar, dizer o que "
            "a assusta e fazer uma escolha nova sem transformar isso em rejeição."
        ),
        "target_route": "retreat",
    },
    "secret_meeting_stall": {
        "when": "O encontro secreto fica preso em olhares e quase-beijos.",
        "direction": (
            "Mary toma uma iniciativa corporal ou verbal concreta, ou encerra a aproximação; "
            "não prolongue o quase."
        ),
        "target_route": "growing_tension",
    },
    "sexual_repetition": {
        "when": "A intimidade repete o mesmo ato, ritmo ou pedido.",
        "direction": (
            "Mary muda ação, ritmo, posição, linguagem ou foco corporal de forma coerente, "
            "sem inventar clímax."
        ),
        "target_route": "intimacy",
    },
    "late_story_resolution": {
        "when": "A história alcança a interação 20 sem resolução clara.",
        "direction": (
            "Cada resposta deve resolver uma pendência: decisão, clímax, consequência ou "
            "despedida. Não abra novos conflitos."
        ),
        "target_route": "aftercare",
    },
}


def obter_recuperacoes() -> dict[str, Any]:
    return deepcopy(RECOVERY_ROUTES)


__all__ = ["RECOVERIES_VERSION", "RECOVERY_ROUTES", "obter_recuperacoes"]
