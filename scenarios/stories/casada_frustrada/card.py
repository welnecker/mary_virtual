from __future__ import annotations

from copy import deepcopy
from typing import Any

from scenarios.card import normalizar_card_package
from scenarios.stories.casada_frustrada.beat_graph import (
    BEAT_GRAPH_VERSION,
    BEATS,
    INITIAL_BEAT,
)
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
from scenarios.stories.casada_frustrada.screenplay_sheet_repository import (
    SCREENPLAY_SPREADSHEET_ID,
    SCREENPLAY_WORKSHEET,
    ScreenplaySheetError,
    inicializar_aba_se_vazia,
)
from scenarios.stories.casada_frustrada.transitions import TRANSITIONS
from scenarios.stories.casada_frustrada.voice import VOICE


CARD_VERSION = "casada-frustrada-card-v5-sheet-screenplay"

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
    "initial_beat": "camera_confirmed",
    "possible_next_routes": ["secret_meeting_plan", "ending"],
    "allowed_actions": ["react", "slow_down", "tease", "advance", "lead", "change_direction"],
    "max_seduction_level": 5,
    "sexual_expression_allowed": True,
    "scene_updates": {"phone_contact_started": True},
    "avoid": [
        "Não transformar a ligação em entrevista.",
        "Não fazer perguntas abstratas sobre intensidade ou preferência.",
        "Não fazer mais de uma pergunta na mesma resposta.",
        "Não atravessar toda a chamada num único turno.",
        "Não narrar ações, excitação ou orgasmo do usuário.",
        "Não usar frases genéricas como recuperar o fôlego, ir devagar ou carinho intenso.",
        "Não oferecer ou iniciar vídeo novamente depois de video_call_established.",
    ],
}
CARD_ROUTES["secret_meeting_plan"] = {
    **deepcopy(CARD_ROUTES.get("secret_meeting_plan", {})),
    "purpose": (
        "Retomar a ligação de madrugada, escolher motel, horário, confirmar presença "
        "e atravessar a ponte para a preparação da manhã seguinte."
    ),
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
        "source": {
            "type": "google_sheets",
            "spreadsheet_id": SCREENPLAY_SPREADSHEET_ID,
            "worksheet": SCREENPLAY_WORKSHEET,
            "fallback": "immersive_screenplay.py",
        },
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
    "beat_graph": {
        "version": BEAT_GRAPH_VERSION,
        "initial_beat": INITIAL_BEAT,
        "beats": deepcopy(BEATS),
        "progression_authority": "code",
        "model_role": "render_current_beat_as_natural_mary_dialogue",
    },
    "transitions": TRANSITIONS,
    "shared_engines": {
        "sexual_engine": True,
        "consent_engine": True,
        "orgasm_guard": True,
        "relationship_metrics_are_advisory": True,
        "orgasm_engine_role": "unlock_or_hold_climax_beats_only",
    },
    "prompt_policy": {
        "character_isolation": True,
        "route_is_authoritative": False,
        "beat_graph_is_progression_authority": True,
        "screenplay_is_authoring_source_not_full_runtime_prompt": True,
        "global_voice_must_not_override_card": True,
        "director_is_advisory": True,
        "model_must_not_choose_route": True,
        "one_question_max": True,
        "organic_injection": True,
        "compact_prompt": True,
        "preserve_physical_profile": True,
        "preserve_psychological_state": True,
    },
}


def obter_card() -> dict[str, Any]:
    try:
        inicializar_aba_se_vazia()
    except ScreenplaySheetError:
        # O card continua disponível com fallback local; a leitura remota tenta novamente
        # quando o contexto do roteiro for montado.
        pass
    return normalizar_card_package(deepcopy(CARD_PACKAGE))


__all__ = ["CARD_PACKAGE", "CARD_VERSION", "obter_card"]
