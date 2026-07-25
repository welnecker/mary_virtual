from __future__ import annotations

from copy import deepcopy
from typing import Any


TRANSITIONS_VERSION = "casada-frustrada-transitions-v2-semantic-bridges"

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
    "bridges": {
        "policy": (
            "Uma ponte é um recurso de continuidade quando uma cena local terminou ou "
            "ficou presa em despedidas equivalentes, mas o arco da história continua. "
            "A decisão é semântica e contextual; não depende de frase fixa nem de uma "
            "quantidade determinada de turnos."
        ),
        "conditions": [
            "a conversa presencial foi realmente encerrada ou já não possui ação útil",
            "não houve recusa definitiva nem pedido explícito para encerrar a história",
            "existe uma próxima situação plausível dentro do roteiro do card",
            "continuar respondendo com outra despedida produziria repetição sem progresso",
        ],
        "options": {
            "supermarket_encounter": {
                "target_route": "aisle_flirtation",
                "target_beat": "second_encounter_in_aisle",
                "possibilities": [
                    "algum tempo depois, Mary cruza novamente com o vizinho em outro corredor",
                    "Mary o reencontra perto do caixa ou de outra seção do supermercado",
                    "o reencontro ocorre mais tarde na garagem ou numa área comum do Plaza",
                ],
            },
            "aisle_flirtation": {
                "target_route": "aisle_flirtation",
                "target_beat": "later_reencounter",
                "possibilities": [
                    "depois de uma despedida real, os dois se cruzam novamente em outra parte do mercado",
                    "o acaso os reúne mais tarde no Plaza e Mary retoma a conversa com mais consciência",
                ],
            },
        },
        "rendering": [
            "usar uma única ponte temporal curta em primeira pessoa",
            "estabelecer somente o novo tempo e local necessários",
            "emendar imediatamente uma fala viva de Mary",
            "não resumir a conversa anterior",
            "não transformar a ponte em narração longa ou roteiro fechado",
        ],
    },
    "ending_semantics": {
        "scene_closing": "fim do local ou bloco atual; não encerra a história",
        "story_ending": "resolução do arco, recusa definitiva ou encerramento explícito",
    },
}


def obter_transicoes() -> dict[str, Any]:
    return deepcopy(TRANSITIONS)


__all__ = ["TRANSITIONS", "TRANSITIONS_VERSION", "obter_transicoes"]
