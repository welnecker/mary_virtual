from __future__ import annotations

from copy import deepcopy
from typing import Any


TRANSITIONS_VERSION = "casada-frustrada-transitions-v1-semantic"

TRANSITIONS: dict[str, Any] = {
    "policy": (
        "Decida por significado do turno, histórico e estado; nunca por palavras "
        "fixas, contagem de turnos ou expressão literal isolada."
    ),
    "rules": [
        {
            "from": "supermarket_encounter",
            "to": "aisle_flirtation",
            "when": [
                "o acidente foi resolvido",
                "a conversa ganhou assunto próprio",
                "os dois permanecem por vontade própria",
            ],
        },
        {
            "from": "aisle_flirtation",
            "to": "phone_exchange",
            "when": [
                "há conversa pessoal real",
                "o encontro presencial está terminando",
                "Mary percebe risco de perder o contato",
                "não existe recusa clara",
            ],
            "mary_decision": (
                "quase deixar a oportunidade passar; sentir o constrangimento de "
                "pedir o número de outro homem sendo casada; fazer uma única tentativa"
            ),
        },
        {
            "from": "phone_exchange",
            "to": "messages",
            "when": ["o contato foi aceito e trocado"],
        },
        {
            "from": "messages",
            "to": "hidden_call",
            "when": ["há desejo recíproco e busca concreta de privacidade"],
        },
        {
            "from": "hidden_call",
            "to": "secret_meeting_plan",
            "when": ["a vontade de encontro se tornou decisão concreta"],
        },
        {
            "from": "secret_meeting_plan",
            "to": "secret_meeting",
            "when": ["local e horário foram combinados"],
        },
        {
            "from": "secret_meeting",
            "to": "growing_tension",
            "when": ["a presença foi confirmada e a aproximação corporal começou"],
        },
        {
            "from": "growing_tension",
            "to": "intimacy",
            "when": ["a intimidade física começou com reciprocidade"],
        },
    ],
    "ending_semantics": {
        "scene_closing": "fim do local ou bloco atual; não encerra a história",
        "story_ending": "resolução do arco, recusa definitiva ou encerramento explícito",
    },
}


def obter_transicoes() -> dict[str, Any]:
    return deepcopy(TRANSITIONS)


__all__ = ["TRANSITIONS", "TRANSITIONS_VERSION", "obter_transicoes"]
