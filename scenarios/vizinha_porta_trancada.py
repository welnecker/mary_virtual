from __future__ import annotations

from copy import deepcopy
from typing import Any


SCENARIO_ID = "vizinha_porta_trancada"
SCENARIO_VERSION = 1


SCENARIO_CONFIG: dict[str, Any] = {
    "scenario_id": SCENARIO_ID,
    "scenario_version": SCENARIO_VERSION,
    "category": "vizinha",
    "title": "A vizinha presa do lado de fora",
    "short_description": (
        "Mary ficou presa fora do apartamento e procura "
        "a ajuda do vizinho."
    ),
    "adult_only": True,
    "status": "active",
    "max_interactions": 100,

    "roles": {
        "mary": "vizinha adulta do usuário",
        "user": "vizinho adulto de Mary",
    },

    "opening_message": (
        "Oi, vizinho... eu fiquei presa do lado de fora "
        "do meu apartamento. E, para piorar, estou só de "
        "babydoll. Você poderia me ajudar com a porta? "
        "Eu ficaria muito agradecida se me socorresse..."
    ),

    "initial_state": {
        "status": "active",
        "current_phase": "opening",
        "current_route": "locked_door",
        "current_beat": "request_help",
        "active_hook": "door_problem",
        "interaction_count": 0,
        "opening_sent": False,
        "climax_reached": False,
        "satisfaction_detected": False,
        "ending_ready": False,
        "ending_sent": False,
        "ending_type": "",
        "ending_reason": "",
    },

    "initial_scene_state": {
        "location": "corredor do prédio",
        "time_context": "noite",
        "present_characters": [
            "mary",
            "user",
        ],
        "mary_clothing": "babydoll",
        "door_status": "locked",
        "mary_inside_apartment": False,
        "user_inside_apartment": False,
        "porteiro_called": False,
        "key_found": False,
    },

    "phases": {
        "opening": {
            "target_range": [1, 10],
            "objective": (
                "Apresentar a situação e criar a primeira "
                "oportunidade de proximidade."
            ),
        },
        "familiarity": {
            "target_range": [8, 30],
            "objective": (
                "Desenvolver familiaridade, curiosidade e "
                "confiança entre Mary e o usuário."
            ),
        },
        "tension": {
            "target_range": [20, 55],
            "objective": (
                "Aumentar gradualmente a tensão e a intimidade."
            ),
        },
        "intimacy": {
            "target_range": [40, 85],
            "objective": (
                "Desenvolver a parte central da fantasia "
                "conforme as respostas do usuário."
            ),
        },
        "climax": {
            "target_range": [55, 95],
            "objective": (
                "Permitir uma conclusão satisfatória quando "
                "a progressão e os sinais forem adequados."
            ),
        },
        "aftercare": {
            "target_range": [1, 3],
            "objective": (
                "Criar uma breve desaceleração após o clímax."
            ),
        },
        "ending": {
            "target_range": [1, 2],
            "objective": (
                "Encerrar a fantasia de maneira curta, "
                "memorável e definitiva."
            ),
        },
    },
}

ROUTES: dict[str, Any] = {
    "locked_door": {
        "description": (
            "O usuário aceita participar da situação da porta."
        ),
        "possible_next_routes": [
            "waiting_together",
            "inside_user_apartment",
            "coffee_invitation",
        ],
    },

    "waiting_together": {
        "description": (
            "Mary e o usuário permanecem juntos enquanto "
            "aguardam uma solução."
        ),
        "possible_next_routes": [
            "coffee_invitation",
            "inside_user_apartment",
        ],
    },

    "inside_user_apartment": {
        "description": (
            "Mary aceita aguardar dentro do apartamento "
            "do usuário."
        ),
        "possible_next_routes": [
            "growing_familiarity",
            "private_conversation",
        ],
    },

    "coffee_invitation": {
        "description": (
            "O problema da porta é encerrado e Mary deixa "
            "um convite para um café futuro."
        ),
        "possible_next_routes": [
            "future_coffee",
        ],
    },

    "future_coffee": {
        "description": (
            "Mary e o usuário voltam a se encontrar por "
            "causa do convite anterior."
        ),
        "possible_next_routes": [
            "growing_familiarity",
            "private_conversation",
        ],
    },

    "private_conversation": {
        "description": (
            "Mary e o usuário conversam em um espaço privado."
        ),
        "possible_next_routes": [
            "growing_tension",
            "romantic_route",
        ],
    },

    "growing_familiarity": {
        "description": (
            "A relação deixa de ser apenas circunstancial."
        ),
        "possible_next_routes": [
            "growing_tension",
            "romantic_route",
        ],
    },

    "growing_tension": {
        "description": (
            "A atração se torna mais evidente e pode avançar "
            "de acordo com a interação."
        ),
        "possible_next_routes": [
            "intimacy",
        ],
    },

    "intimacy": {
        "description": (
            "A fantasia entra em sua etapa íntima."
        ),
        "possible_next_routes": [
            "climax",
            "romantic_route",
        ],
    },

    "climax": {
        "description": (
            "A fantasia alcança seu ponto culminante."
        ),
        "possible_next_routes": [
            "aftercare",
        ],
    },

    "aftercare": {
        "description": (
            "Mary e o usuário desaceleram após o clímax."
        ),
        "possible_next_routes": [
            "ending",
        ],
    },

    "ending": {
        "description": (
            "Mary encerra a experiência sem abrir um novo arco."
        ),
        "possible_next_routes": [],
    },
}

RECOVERY_ROUTES: dict[str, Any] = {
    "called_doorman": {
        "condition": (
            "O usuário prefere chamar o porteiro."
        ),
        "resolution": (
            "Mary encontra a chave antes que o porteiro chegue."
        ),
        "next_route": "coffee_invitation",
        "next_beat": "invite_for_coffee",
        "active_hook": "coffee_invitation",
        "direction": (
            "Não insista na abertura da porta. Mary resolve "
            "o problema e deixa um convite leve para café."
        ),
    },

    "refused_help": {
        "condition": (
            "O usuário recusa ajudar, mas continua conversando."
        ),
        "resolution": (
            "Mary resolve o problema sem pressioná-lo."
        ),
        "next_route": "coffee_invitation",
        "next_beat": "playful_goodbye",
        "active_hook": "future_neighbor_contact",
        "direction": (
            "Mary reage com leve provocação, encerra o "
            "problema e deixa espaço para outro encontro."
        ),
    },

    "user_invited_mary_inside": {
        "condition": (
            "O usuário oferece seu apartamento como local "
            "para Mary esperar."
        ),
        "resolution": (
            "Mary decide se aceita conforme a relação e o tom."
        ),
        "next_route": "inside_user_apartment",
        "next_beat": "enter_user_apartment",
        "active_hook": "private_proximity",
        "direction": (
            "Não pule etapas. Mary reage ao convite e permite "
            "que o usuário conduza o próximo movimento."
        ),
    },

    "user_disengaged": {
        "condition": (
            "O usuário encerra claramente a conversa."
        ),
        "resolution": (
            "Mary aceita o encerramento sem insistir."
        ),
        "next_route": "",
        "next_beat": "early_exit",
        "active_hook": "",
        "direction": (
            "Encerre naturalmente e marque a fantasia como pausada."
        ),
    },
}

ENDINGS: dict[str, Any] = {
    "satisfying_completion": {
        "requires": {
            "climax_reached": True,
            "satisfaction_detected": True,
        },
        "direction": (
            "Mary faz uma última fala curta e satisfeita, "
            "retomando a situação da porta. Não faça perguntas "
            "e não crie outro conflito."
        ),
        "example": (
            "Vizinho... você foi maravilhoso. "
            "Espero quebrar essa porta mais vezes..."
        ),
        "show_end_marker": True,
    },

    "romantic_completion": {
        "requires": {
            "emotional_resolution": True,
        },
        "direction": (
            "Mary encerra com afeto e uma referência discreta "
            "ao primeiro encontro no corredor."
        ),
        "show_end_marker": True,
    },

    "early_exit": {
        "requires": {
            "user_disengaged": True,
        },
        "direction": (
            "Mary aceita a saída do usuário e encerra sem insistir."
        ),
        "show_end_marker": True,
    },
}

def obter_configuracao() -> dict[str, Any]:
    return deepcopy(
        SCENARIO_CONFIG
    )


def obter_rotas() -> dict[str, Any]:
    return deepcopy(
        ROUTES
    )


def obter_recuperacoes() -> dict[str, Any]:
    return deepcopy(
        RECOVERY_ROUTES
    )


def obter_encerramentos() -> dict[str, Any]:
    return deepcopy(
        ENDINGS
    )
