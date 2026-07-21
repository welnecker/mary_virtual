from __future__ import annotations

from copy import deepcopy
from typing import Any

from scenarios.schema import (
    ACCESS_TYPE_FREE,
    normalizar_config_cenario,
)


SCENARIO_ID = "vizinha_porta_trancada"
SCENARIO_VERSION = 2


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
    "display_order": 1,

    # Compatibilidade temporária com partes antigas do app.
    # O novo controle de duração está no bloco duration.
    "max_interactions": 58,

    "card": {
        "title": "A vizinha presa do lado de fora",
        "subtitle": (
            "Ela precisa de ajuda. A proximidade pode transformar "
            "uma noite comum em algo bem mais íntimo."
        ),
        "image": (
            "assets/scenarios/"
            "vizinha_porta_trancada/card.webp"
        ),
        "badge": "Degustação",
        "button_label_free": "Jogar gratuitamente",
        "button_label_locked": "Desbloquear",
        "button_label_unlocked": "Jogar",
    },

    "duration": {
        "target_interactions": 48,
        "soft_ending_start": 40,
        "hard_ending_limit": 58,
        "ending_turns": 2,
    },

    # Esta será a única historinha gratuita do catálogo.
    "commerce": {
        "access_type": ACCESS_TYPE_FREE,
        "price_cents": 0,
        "currency": "BRL",
        "product_id": "",
    },

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
        "input_locked": False,
        "show_return_to_menu": False,
    },

    "initial_scene_state": {
        "current_phase": "opening",
        "current_route": "locked_door",
        "current_beat": "request_help",
        "active_hook": "door_problem",

        "scene_active": True,
        "fantasy_established": True,
        "opening_sent": False,
        "interaction_count": 0,

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

        "completed_beats": [],
        "failed_beats": [],
        "pending_events": [],
        "last_user_action": "",
        "last_director_decision": "",

        "climax_reached": False,
        "satisfaction_detected": False,
        "ending_ready": False,
        "ending_sent": False,
        "input_locked": False,
        "show_return_to_menu": False,
    },

    "internal_monologue": {
        "enabled": True,
        "format": "markdown_italic",
        "max_sentences": 1,
        "max_words": 24,
        "frequency_by_phase": {
            "opening": 0.35,
            "familiarity": 0.45,
            "tension": 0.70,
            "intimacy": 0.80,
            "climax": 0.55,
            "aftercare": 0.35,
            "ending": 0.15,
        },
        "purposes_by_phase": {
            "opening": [
                "embarrassment",
                "curiosity",
                "hidden_attraction",
            ],
            "familiarity": [
                "curiosity",
                "growing_attraction",
                "anticipation",
            ],
            "tension": [
                "hidden_attraction",
                "sexual_desire",
                "anticipation",
            ],
            "intimacy": [
                "sexual_desire",
                "emotional_exposure",
                "anticipation",
            ],
            "climax": [
                "pleasure",
                "emotional_intensity",
            ],
            "aftercare": [
                "satisfaction",
                "affection",
                "vulnerability",
            ],
            "ending": [
                "satisfaction",
                "playful_memory",
            ],
        },
        "rules": [
            (
                "O pensamento pertence exclusivamente a Mary e não é "
                "ouvido pelo usuário nem por outros personagens."
            ),
            "O pensamento deve ser escrito em primeira pessoa.",
            (
                "O pensamento deve revelar algo que Mary não disse "
                "diretamente na fala."
            ),
            (
                "O pensamento não deve repetir a fala com outras palavras."
            ),
            (
                "O pensamento não pode afirmar como fato aquilo que "
                "o usuário pensa, sente, deseja ou pretende."
            ),
            (
                "O pensamento deve permanecer coerente com a fase, "
                "a relação e o estado atual da cena."
            ),
            "Não antecipar fatos que ainda não aconteceram.",
            (
                "Não explicar o roteiro ou mencionar que a situação "
                "é uma fantasia."
            ),
        ],
    },

    # As faixas orientam o diretor, mas não obrigam a história
    # a permanecer em cada etapa até atingir um número fixo.
    "phases": {
        "opening": {
            "target_range": [1, 5],
            "objective": (
                "Apresentar o problema da porta e criar a primeira "
                "oportunidade de proximidade."
            ),
        },
        "familiarity": {
            "target_range": [4, 14],
            "objective": (
                "Desenvolver familiaridade, humor, curiosidade e uma "
                "oportunidade concreta de permanecerem juntos."
            ),
        },
        "tension": {
            "target_range": [10, 26],
            "objective": (
                "Transformar a proximidade circunstancial em atração, "
                "provocação e escolhas com consequência."
            ),
        },
        "intimacy": {
            "target_range": [20, 40],
            "objective": (
                "Desenvolver a parte íntima da fantasia conforme as "
                "decisões e os limites dos dois."
            ),
        },
        "climax": {
            "target_range": [34, 50],
            "objective": (
                "Entregar a resolução principal quando a progressão "
                "e o estado sexual permitirem."
            ),
        },
        "aftercare": {
            "target_range": [1, 3],
            "objective": (
                "Criar uma desaceleração breve e coerente depois da "
                "resolução principal."
            ),
        },
        "ending": {
            "target_range": [1, 2],
            "objective": (
                "Encerrar a historinha de maneira curta, marcante e "
                "definitiva, sem abrir outro arco."
            ),
        },
    },
}


def obter_configuracao() -> dict[str, Any]:
    """Retorna uma cópia validada e normalizada da configuração."""

    return normalizar_config_cenario(
        deepcopy(
            SCENARIO_CONFIG
        )
    )


__all__ = [
    "SCENARIO_CONFIG",
    "SCENARIO_ID",
    "SCENARIO_VERSION",
    "obter_configuracao",
]
