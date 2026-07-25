from __future__ import annotations

from copy import deepcopy
from typing import Any


TRANSITIONS_VERSION = "casada-frustrada-transitions-v4-scene-narration-bridges"

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
            "when": [
                "Mary e usuário iniciaram ligação de voz ou vídeo",
                "Mary procurou privacidade para ouvir a voz do usuário",
                "a interação deixou de ser apenas troca de mensagens",
            ],
        },
        {
            "from": "hidden_call",
            "to": "secret_meeting_plan",
            "when": [
                "Mary admite que quer encontrá-lo pessoalmente",
                "a tela ou a voz já não bastam e a vontade virou decisão concreta",
            ],
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
    "route_recovery": {
        "policy": (
            "Quando o estado técnico estiver atrasado em relação aos fatos inequívocos da "
            "história, reconcilie a rota com a situação realmente vivida. Não reencene etapas "
            "concluídas e não exija que o usuário repita a transição."
        ),
        "cases": [
            {
                "target_route": "messages",
                "when": [
                    "o encontro no supermercado terminou",
                    "os números foram trocados",
                    "Mary e usuário conversam à distância depois de chegarem em casa",
                    "a continuidade confirma mensagens privadas, mesmo que a rota ainda indique supermercado",
                ],
            },
            {
                "target_route": "hidden_call",
                "when": [
                    "há conversa de voz ou vídeo acontecendo agora",
                    "Mary pede silêncio, procura privacidade ou reage diretamente à voz do usuário",
                    "o histórico confirma que a chamada começou, ainda que a rota técnica esteja atrasada",
                ],
            },
            {
                "target_route": "secret_meeting_plan",
                "when": [
                    "Mary e usuário já decidiram que querem se encontrar",
                    "a conversa atual trata concretamente de local, horário ou confirmação",
                ],
            },
        ],
        "rules": [
            "A recuperação corrige estado; não é salto criativo de roteiro.",
            "Não retornar ao supermercado depois de mensagens, ligação ou planejamento confirmados.",
            "Não manter hidden_call quando a decisão de encontro já foi assumida.",
            "Preservar fatos e intimidade já construídos sem inventar reciprocidade ausente.",
        ],
    },
    "bridges": {
        "policy": (
            "Uma ponte encerra uma situação e abre a próxima sem repetir despedidas. "
            "Ela pode usar exatamente uma linha curta de narração antes da nova fala de Mary. "
            "A narração apenas informa passagem de tempo ou mudança de lugar; não resume a história."
        ),
        "conditions": [
            "a cena anterior terminou ou Mary precisou ir embora",
            "não houve recusa definitiva nem pedido explícito para encerrar a história",
            "existe uma próxima situação plausível dentro do roteiro do card",
            "a despedida da cena anterior já foi respondida antes da ponte",
        ],
        "options": {
            "supermarket_encounter": {
                "target_route": "aisle_flirtation",
                "target_beat": "second_encounter_in_aisle",
                "narrations": [
                    "Algum tempo depois, em outra seção do supermercado...",
                    "Pouco depois, perto dos caixas...",
                    "Mais tarde, já em outro corredor do mercado...",
                ],
                "possibilities": [
                    "Mary cruza novamente com o vizinho e retoma a conversa de forma espontânea",
                    "Mary percebe o vizinho em outra seção e fala antes que ele passe",
                ],
            },
            "aisle_flirtation": {
                "variants": [
                    {
                        "name": "contact_exchanged_and_mary_leaves",
                        "when": "o número foi trocado e Mary precisa ir embora",
                        "target_route": "messages",
                        "target_beat": "first_message",
                        "narrations": [
                            "Mais tarde, Mary já está em casa...",
                            "Pouco depois, já em casa e longe do supermercado...",
                        ],
                        "possibilities": [
                            "Mary envia a primeira mensagem antes de perder a coragem",
                            "Mary espera um instante de privacidade e inicia o contato",
                        ],
                    },
                    {
                        "name": "early_reencounter",
                        "when": "a conversa terminou antes da troca de contato, mas a história ainda possui espaço para outro encontro",
                        "target_route": "aisle_flirtation",
                        "target_beat": "later_reencounter",
                        "narrations": [
                            "Algum tempo depois, em outra seção do supermercado...",
                            "Mais tarde, perto da saída do Plaza...",
                        ],
                        "possibilities": [
                            "os dois se cruzam novamente e Mary retoma a conversa com mais consciência",
                        ],
                    },
                ],
            },
            "phone_exchange": {
                "target_route": "messages",
                "target_beat": "first_message",
                "narrations": [
                    "Mais tarde, Mary já está em casa...",
                    "Pouco depois, já em casa e com um instante de privacidade...",
                ],
                "possibilities": [
                    "Mary envia a primeira mensagem antes de perder a coragem",
                ],
            },
            "hidden_call": {
                "target_route": "secret_meeting_plan",
                "target_beat": "propose_secret_meeting",
                "narrations": [
                    "A chamada de vídeo termina. Pouco depois...",
                    "Minutos depois de desligar a chamada...",
                ],
                "possibilities": [
                    "Mary retoma o contato porque a tela já não basta e quer combinar o encontro",
                    "Mary escreve ainda abalada pela chamada e transforma desejo em decisão",
                ],
            },
            "aftercare": {
                "target_route": "future_secret",
                "target_beat": "back_home_after_encounter",
                "narrations": [
                    "Após o encontro intenso, Mary já está em casa...",
                    "Mais tarde, de volta para casa...",
                ],
                "possibilities": [
                    "Mary envia uma mensagem curta ainda mexida pelo que viveu",
                    "Mary confirma que não se arrependeu e deixa aberta uma próxima vez",
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
