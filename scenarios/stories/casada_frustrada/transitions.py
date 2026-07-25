from __future__ import annotations

from copy import deepcopy
from typing import Any


TRANSITIONS_VERSION = "casada-frustrada-transitions-v5-active-scene-bridges"

TRANSITIONS: dict[str, Any] = {
    "policy": (
        "Decida por significado do turno, histórico e estado; nunca por palavras "
        "fixas, contagem de turnos ou expressão literal isolada."
    ),
    "rules": [
        {"from": "supermarket_encounter", "to": "aisle_flirtation", "when": ["o acidente foi resolvido", "a conversa ganhou assunto próprio", "os dois permanecem por vontade própria"]},
        {"from": "aisle_flirtation", "to": "phone_exchange", "when": ["há conversa pessoal real", "o encontro presencial está terminando", "Mary percebe risco de perder o contato", "não existe recusa clara"], "mary_decision": "quase deixar a oportunidade passar; sentir o constrangimento de pedir o número; fazer uma única tentativa"},
        {"from": "phone_exchange", "to": "messages", "when": ["o contato foi aceito e trocado"]},
        {"from": "messages", "to": "hidden_call", "when": ["Mary e usuário iniciaram ligação de voz ou vídeo", "Mary procurou privacidade", "a interação deixou de ser apenas troca de mensagens"]},
        {"from": "hidden_call", "to": "secret_meeting_plan", "when": ["Mary admite que quer encontrá-lo", "a tela ou a voz já não bastam e a vontade virou decisão"]},
        {"from": "secret_meeting_plan", "to": "secret_meeting", "when": ["local e horário foram combinados"]},
        {"from": "secret_meeting", "to": "growing_tension", "when": ["a presença foi confirmada e a aproximação corporal começou"]},
        {"from": "growing_tension", "to": "intimacy", "when": ["a intimidade física começou com reciprocidade"]},
    ],
    "route_recovery": {
        "policy": "Quando o estado técnico estiver atrasado, reconcilie a rota com a situação realmente vivida, sem reencenar etapas concluídas.",
        "cases": [
            {"target_route": "messages", "when": ["o encontro terminou", "os números foram trocados", "Mary e usuário conversam à distância depois de chegarem em casa"]},
            {"target_route": "hidden_call", "when": ["há conversa de voz ou vídeo acontecendo", "Mary procurou privacidade ou reage à voz do usuário"]},
            {"target_route": "secret_meeting_plan", "when": ["os dois decidiram se encontrar", "a conversa trata de local, horário ou confirmação"]},
        ],
        "rules": ["A recuperação corrige estado; não é salto criativo.", "Não retornar ao supermercado depois de mensagens ou ligação confirmadas.", "Não manter hidden_call quando a decisão de encontro já foi assumida."],
    },
    "bridges": {
        "policy": (
            "Uma ponte encerra uma situação e abre a próxima sem repetir despedidas. "
            "Use exatamente uma linha curta de narração antes da nova fala de Mary."
        ),
        "conditions": [
            "a cena anterior terminou ou Mary precisou ir embora",
            "não houve recusa definitiva",
            "existe uma próxima situação prevista no roteiro",
            "a despedida já foi respondida antes da ponte",
        ],
        "options": {
            "supermarket_encounter": {
                "target_route": "aisle_flirtation",
                "target_beat": "second_encounter_in_aisle",
                "possibilities": [
                    "Algum tempo depois, em outra seção do supermercado, Mary cruza novamente com o vizinho e retoma a conversa.",
                    "Pouco depois, perto dos caixas, Mary percebe o vizinho e fala antes que ele passe.",
                ],
            },
            "aisle_flirtation": {
                "target_route": "messages",
                "target_beat": "first_message",
                "possibilities": [
                    "Mais tarde, Mary já está em casa e envia a primeira mensagem antes de perder a coragem.",
                    "Pouco depois, já em casa e com um instante de privacidade, Mary inicia o contato.",
                ],
            },
            "phone_exchange": {
                "target_route": "messages",
                "target_beat": "first_message",
                "possibilities": [
                    "Mais tarde, Mary já está em casa e envia a primeira mensagem antes de perder a coragem.",
                    "Pouco depois, já em casa e longe do supermercado, Mary inicia o contato.",
                ],
            },
            "hidden_call": {
                "target_route": "secret_meeting_plan",
                "target_beat": "propose_secret_meeting",
                "possibilities": [
                    "A chamada de vídeo termina. Pouco depois, Mary escreve porque a tela já não basta e quer combinar o encontro.",
                    "Minutos depois de desligar a chamada, Mary transforma o desejo em uma decisão concreta.",
                ],
            },
            "aftercare": {
                "target_route": "future_secret",
                "target_beat": "back_home_after_encounter",
                "possibilities": [
                    "Após o encontro intenso, Mary já está em casa e envia uma mensagem ainda mexida pelo que viveu.",
                    "Mais tarde, de volta para casa, Mary confirma que não se arrependeu e deixa aberta uma próxima vez.",
                ],
            },
        },
        "rendering": [
            "usar exatamente uma linha curta de narração",
            "a narração pode estar em terceira pessoa e deve terminar antes da fala de Mary",
            "depois da narração, escrever uma fala nova de Mary em primeira pessoa",
            "não responder novamente à despedida anterior",
            "não resumir a conversa ou o encontro concluído",
            "não transformar a ponte em parágrafo literário",
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
