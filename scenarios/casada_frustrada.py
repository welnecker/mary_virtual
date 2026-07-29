from __future__ import annotations

from copy import deepcopy
from typing import Any

from scenarios.schema import ACCESS_TYPE_PAID, normalizar_config_cenario
from scenarios.stories.casada_frustrada.chapters.cap_01.config import CHAPTER


PUBLIC_SCENARIO_MODULE_VERSION = "casada-frustrada-public-v2-clean"
SCENARIO_ID = "casada_frustrada"
SCENARIO_VERSION = 5
ROUTES_VERSION = "casada-frustrada-routes-v2-clean"
RECOVERIES_VERSION = "casada-frustrada-recoveries-v2-clean"
ENDINGS_VERSION = "casada-frustrada-endings-v2-clean"


def _build_routes() -> dict[str, Any]:
    routes: dict[str, Any] = {}
    ordered_beats = list(CHAPTER.beats.values())
    for index, beat in enumerate(ordered_beats):
        route = routes.setdefault(
            beat.route,
            {
                "route_id": beat.route,
                "initial_beat": beat.beat_id,
                "possible_next_routes": [],
            },
        )
        if index + 1 < len(ordered_beats):
            next_route = ordered_beats[index + 1].route
            if next_route != beat.route and next_route not in route["possible_next_routes"]:
                route["possible_next_routes"].append(next_route)
    return routes


SCENARIO_CONFIG: dict[str, Any] = {
    "scenario_id": SCENARIO_ID,
    "scenario_version": SCENARIO_VERSION,
    "category": "encontro_secreto",
    "title": "Casada frustrada",
    "short_description": "Um esbarrão no supermercado desperta em Mary uma possibilidade inesperada.",
    "adult_only": True,
    "status": "active",
    "display_order": 2,
    "max_interactions": 95,
    "card": {
        "title": "Casada frustrada",
        "subtitle": "Um encontro casual inicia uma história interativa em capítulos.",
        "image": "",
        "badge": "Encontro secreto",
        "button_label_free": "Começar a história",
        "button_label_locked": "Desbloquear por Pix",
        "button_label_unlocked": "Jogar",
    },
    "duration": {
        "target_interactions": 92,
        "soft_ending_start": 90,
        "hard_ending_limit": 95,
        "ending_turns": 3,
        "count_is_advisory": True,
        "allow_early_resolution": True,
    },
    "commerce": {
        "access_type": ACCESS_TYPE_PAID,
        "price_cents": 990,
        "currency": "BRL",
        "product_id": "story_casada_frustrada_v1",
    },
    "roles": {
        "mary": "mulher adulta vivendo a história em primeira pessoa",
        "user": "homem adulto que conhece Mary por acaso no supermercado",
    },
    "premise": {
        "location": "supermercado de bairro",
        "time_context": "fim de tarde",
        "situation": "Mary esbarra casualmente no usuário durante as compras.",
    },
    "opening_message": "Eita, caralho... desculpa!",
    "initial_state": {
        "status": "active",
        "current_phase": "opening",
        "current_route": CHAPTER.initial_route,
        "current_beat": CHAPTER.initial_beat,
        "interaction_count": 0,
        "opening_sent": False,
        "ending_ready": False,
        "ending_sent": False,
        "input_locked": False,
        "show_return_to_menu": False,
    },
    "initial_scene_state": {
        "current_phase": "opening",
        "current_route": CHAPTER.initial_route,
        "current_beat": CHAPTER.initial_beat,
        "scene_active": True,
        "opening_sent": False,
        "interaction_count": 0,
        "location": "supermercado de bairro",
        "time_context": "fim de tarde",
        "present_characters": ["mary", "user"],
        "completed_beats": [],
        "failed_beats": [],
        "pending_events": [],
        "resolved_elements": [],
        "ending_ready": False,
        "ending_sent": False,
        "input_locked": False,
        "show_return_to_menu": False,
    },
    "phases": {
        "opening": {"objective": "Resolver o esbarrão e iniciar o primeiro contato."},
        "familiarity": {"objective": "Construir reconhecimento, conversa e aproximação."},
        "tension": {"objective": "Transformar interesse em desejo e decisão concreta."},
        "intimacy": {"objective": "Desenvolver intimidade com reciprocidade e continuidade."},
        "climax": {"objective": "Concluir a progressão corporal autorizada pelo estado."},
        "aftercare": {"objective": "Mostrar consequência, presença e desaceleração."},
        "ending": {"objective": "Encerrar o capítulo com uma conclusão clara ou gancho."},
    },
    "narrative_rules": [
        "Executar somente o beat atual.",
        "Introduzir no máximo um movimento narrativo novo por resposta.",
        "Não inventar ações ou decisões do usuário.",
    ],
}

ROUTES: dict[str, Any] = _build_routes()
RECOVERY_ROUTES: dict[str, Any] = {}
ENDINGS: dict[str, Any] = {}


def obter_configuracao() -> dict[str, Any]:
    return normalizar_config_cenario(deepcopy(SCENARIO_CONFIG))


def obter_rotas() -> dict[str, Any]:
    return deepcopy(ROUTES)


def obter_recuperacoes() -> dict[str, Any]:
    return deepcopy(RECOVERY_ROUTES)


def obter_encerramentos() -> dict[str, Any]:
    return deepcopy(ENDINGS)


__all__ = [
    "PUBLIC_SCENARIO_MODULE_VERSION",
    "SCENARIO_ID",
    "SCENARIO_VERSION",
    "SCENARIO_CONFIG",
    "ROUTES_VERSION",
    "ROUTES",
    "RECOVERIES_VERSION",
    "RECOVERY_ROUTES",
    "ENDINGS_VERSION",
    "ENDINGS",
    "obter_configuracao",
    "obter_rotas",
    "obter_recuperacoes",
    "obter_encerramentos",
]
