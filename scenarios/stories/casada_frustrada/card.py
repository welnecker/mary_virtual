from __future__ import annotations

from copy import deepcopy
from typing import Any

from scenarios.card import normalizar_card_package
from scenarios.stories.casada_frustrada.call_screenplay import (
    HIDDEN_CALL_DIALOGUE,
    SECRET_MEETING_PLAN_DIALOGUE,
)
from scenarios.stories.casada_frustrada.character import CHARACTER
from scenarios.stories.casada_frustrada.psychology import PSYCHOLOGY
from scenarios.stories.casada_frustrada.routes import ROUTES
from scenarios.stories.casada_frustrada.screenplay import (
    SECRET_MEETING_DIALOGUE,
    SUPERMARKET_DIALOGUE,
    SUPERMARKET_ROUTES,
    MESSAGES_DIALOGUE,
)
from scenarios.stories.casada_frustrada.transitions import TRANSITIONS
from scenarios.stories.casada_frustrada.voice import VOICE


CARD_VERSION = "casada-frustrada-card-v2-separated-call"

CARD_ROUTES = deepcopy(ROUTES)
CARD_ROUTES["messages"] = {
    **deepcopy(CARD_ROUTES.get("messages", {})),
    "purpose": (
        "Retomar contato, admitir o impacto do encontro e buscar uma ligação privada "
        "sem transformar mensagens em conversa doméstica infinita."
    ),
    "possible_next_routes": ["hidden_call", "secret_meeting_plan", "ending"],
    "avoid": [
        "Não começar explicitamente sexual.",
        "Não transformar mensagens em entrevista.",
        "Não repetir reclamações sobre o casamento.",
        "Não permanecer indefinidamente falando de compras, sofá, rotina ou ex-relacionamentos.",
        "Quando Mary quiser ouvir ou ver o usuário, avançar para hidden_call.",
    ],
}
CARD_ROUTES["hidden_call"] = {
    **deepcopy(CARD_ROUTES.get("hidden_call", {})),
    "block": "LIGAÇÃO PRIVADA — VOZ, RISCO E DESEJO",
    "description": (
        "Mary conseguiu privacidade parcial para ouvir a voz do usuário. A chamada "
        "começa cautelosa e vulnerável, torna-se corporal com reciprocidade e termina "
        "em vontade concreta de encontro."
    ),
    "mary_state": ["cautelosa", "nervosa", "carente", "progressivamente desejante"],
    "purpose": (
        "Transformar carência em desejo concreto por meio da voz, da privacidade, "
        "do risco e da reciprocidade; preparar a decisão de encontro."
    ),
    "phase": "tension",
    "allowed_phases": ["familiarity", "tension", "intimacy"],
    "initial_beat": "seek_privacy",
    "beats": [
        "seek_privacy",
        "voice_contact",
        "voice_effect",
        "brief_vulnerability",
        "visual_contact_offer",
        "desire_confirmed",
        "meeting_desire",
    ],
    "possible_next_routes": ["secret_meeting_plan", "retreat", "ending"],
    "allowed_actions": ["react", "slow_down", "tease", "advance", "lead", "change_direction"],
    "max_seduction_level": 5,
    "sexual_expression_allowed": True,
    "scene_updates": {"phone_contact_started": True},
    "entry_when": [
        "A ligação privada começou.",
        "Mary buscou um lugar onde pudesse ouvir a voz do usuário com menor risco.",
    ],
    "stay_while": [
        "A voz e a presença à distância ainda estão produzindo aproximação real.",
        "Mary ainda não admitiu claramente que quer encontrá-lo.",
    ],
    "exit_when": [
        "Mary admite que mensagens e tela já não bastam e decide marcar encontro.",
        "Algum risco ou hesitação exige retreat.",
        "A chamada termina sem decisão.",
    ],
    "avoid": [
        "Não transformar a ligação em entrevista sobre sofá, compras, rotina ou ex-namorada.",
        "Não repetir discursos sobre o marido, o casamento ou a solidão doméstica.",
        "Não começar a chamada com nudez ou sexualidade explícita.",
        "Não atravessar privacidade, voz, vídeo, excitação e encontro no mesmo turno.",
        "Não narrar ações, excitação ou orgasmo do usuário.",
        "Não permanecer na ligação depois que a decisão de encontro amadureceu.",
    ],
}
CARD_ROUTES["secret_meeting_plan"] = {
    **deepcopy(CARD_ROUTES.get("secret_meeting_plan", {})),
    "purpose": "Converter a vontade assumida na ligação em local, horário e confirmação.",
    "avoid": [
        "Não adiar indefinidamente.",
        "Não voltar à conversa banal.",
        "Não reiniciar o supermercado.",
        "Não refazer toda a ligação erótica depois que a decisão foi tomada.",
    ],
}

CARD_PACKAGE: dict[str, Any] = {
    "scenario_id": "casada_frustrada",
    "character": CHARACTER,
    "psychology": PSYCHOLOGY,
    "voice": VOICE,
    "routes": CARD_ROUTES,
    "screenplay": {
        "route_groups": {
            "supermarket": sorted(SUPERMARKET_ROUTES),
            "messages": ["messages"],
            "hidden_call": ["hidden_call"],
            "secret_meeting_plan": ["secret_meeting_plan"],
            "secret_meeting": [
                "secret_meeting",
                "growing_tension",
                "intimacy",
                "climax",
                "aftercare",
                "future_secret",
            ],
        },
        "blocks": {
            "supermarket": SUPERMARKET_DIALOGUE,
            "messages": MESSAGES_DIALOGUE,
            "hidden_call": HIDDEN_CALL_DIALOGUE,
            "secret_meeting_plan": SECRET_MEETING_PLAN_DIALOGUE,
            "secret_meeting": SECRET_MEETING_DIALOGUE,
        },
    },
    "transitions": TRANSITIONS,
    "shared_engines": {
        "sexual_engine": True,
        "consent_engine": True,
        "orgasm_guard": True,
        "relationship_metrics_are_advisory": True,
    },
    "prompt_policy": {
        "character_isolation": True,
        "route_is_authoritative": True,
        "screenplay_is_lexical_source": True,
        "global_voice_must_not_override_card": True,
        "director_must_recommend_route_semantically": True,
    },
}


def obter_card() -> dict[str, Any]:
    return normalizar_card_package(deepcopy(CARD_PACKAGE))


__all__ = ["CARD_PACKAGE", "CARD_VERSION", "obter_card"]
