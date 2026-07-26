from __future__ import annotations

from copy import deepcopy
from typing import Any

from scenarios.card import normalizar_card_package
from scenarios.stories.casada_frustrada.character import CHARACTER
from scenarios.stories.casada_frustrada.immersive_screenplay import (
    HIDDEN_CALL_DIALOGUE,
    MESSAGES_DIALOGUE,
    SECRET_MEETING_DIALOGUE,
    SECRET_MEETING_PLAN_DIALOGUE,
    SUPERMARKET_DIALOGUE,
)
from scenarios.stories.casada_frustrada.psychology import PSYCHOLOGY
from scenarios.stories.casada_frustrada.routes import ROUTES
from scenarios.stories.casada_frustrada.transitions import TRANSITIONS
from scenarios.stories.casada_frustrada.voice import VOICE


CARD_VERSION = "casada-frustrada-card-v3-immersive-screenplay"

SUPERMARKET_ROUTES = {
    "supermarket_encounter",
    "aisle_flirtation",
    "phone_exchange",
}

CARD_ROUTES = deepcopy(ROUTES)
CARD_ROUTES["messages"] = {
    **deepcopy(CARD_ROUTES.get("messages", {})),
    "purpose": (
        "Retomar contato, admitir o impacto do encontro e buscar uma chamada privada "
        "sem transformar mensagens em conversa doméstica infinita."
    ),
    "possible_next_routes": ["hidden_call", "ending"],
    "avoid": [
        "Não começar explicitamente sexual.",
        "Não transformar mensagens em entrevista.",
        "Não repetir reclamações sobre o casamento.",
        "Não permanecer indefinidamente falando de compras, sofá ou rotina.",
        "Não fazer mais de uma pergunta na mesma resposta.",
        "Quando Mary quiser ouvir ou ver o usuário, avançar para hidden_call.",
        "Se o usuário recusar definitivamente atender a chamada, encerrar sem insistência.",
    ],
}
CARD_ROUTES["hidden_call"] = {
    **deepcopy(CARD_ROUTES.get("hidden_call", {})),
    "block": "LIGAÇÃO PRIVADA — VOZ, VÍDEO E DESEJO",
    "description": (
        "Mary conseguiu privacidade no banheiro. A chamada começa pela voz e pelo "
        "contato visual, cresce por iniciativas concretas e termina quando ela precisa "
        "desligar e decide ligar novamente de madrugada."
    ),
    "mary_state": ["nervosa", "carente", "excitada", "progressivamente ousada"],
    "purpose": (
        "Transformar atração em desejo corporal por meio da voz, do vídeo, do risco "
        "doméstico e da reciprocidade, sem perguntas abstratas."
    ),
    "phase": "tension",
    "allowed_phases": ["tension", "intimacy"],
    "initial_beat": "seek_privacy",
    "beats": [
        "seek_privacy",
        "voice_contact",
        "camera_positioned",
        "shirt_request",
        "underwear_reveal",
        "mary_reveal",
        "mutual_stimulation",
        "user_resolution",
        "mary_unfinished",
        "call_ends",
    ],
    "possible_next_routes": ["secret_meeting_plan", "ending"],
    "allowed_actions": ["react", "slow_down", "tease", "advance", "lead", "change_direction"],
    "max_seduction_level": 5,
    "sexual_expression_allowed": True,
    "scene_updates": {"phone_contact_started": True},
    "entry_when": [
        "A chamada privada começou.",
        "Mary conseguiu privacidade suficiente para usar voz ou vídeo.",
    ],
    "stay_while": [
        "A chamada ainda avança por um movimento concreto de cada vez.",
        "A primeira resolução à distância ainda não ocorreu.",
    ],
    "exit_when": [
        "Mary precisa desligar depois da resolução do usuário e promete ligar de madrugada.",
        "O usuário recusa definitivamente atender ou continuar a chamada.",
    ],
    "avoid": [
        "Não transformar a ligação em entrevista.",
        "Não fazer perguntas abstratas sobre intensidade ou preferência.",
        "Não fazer mais de uma pergunta na mesma resposta.",
        "Não atravessar toda a chamada num único turno.",
        "Não narrar ações, excitação ou orgasmo do usuário.",
        "Não usar frases genéricas como recuperar o fôlego, ir devagar ou carinho intenso.",
    ],
}
CARD_ROUTES["secret_meeting_plan"] = {
    **deepcopy(CARD_ROUTES.get("secret_meeting_plan", {})),
    "purpose": (
        "Retomar a ligação de madrugada, escolher motel, horário, confirmar presença "
        "e atravessar a ponte para a preparação da manhã seguinte."
    ),
    "beats": [
        "late_night_call",
        "propose_motel",
        "name_location",
        "agree_time",
        "confirm_attendance",
        "morning_preparation",
        "motel_arrival",
    ],
    "avoid": [
        "Não adiar indefinidamente.",
        "Não voltar à conversa banal.",
        "Não reiniciar o supermercado.",
        "Não fazer mais de uma pergunta na mesma resposta.",
        "Se o usuário recusar definitivamente ou não comparecer, encerrar sem Mary insistir.",
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
        "one_question_max": True,
        "organic_injection": True,
    },
}


def obter_card() -> dict[str, Any]:
    return normalizar_card_package(deepcopy(CARD_PACKAGE))


__all__ = ["CARD_PACKAGE", "CARD_VERSION", "obter_card"]
