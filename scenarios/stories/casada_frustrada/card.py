from __future__ import annotations

from copy import deepcopy
from typing import Any

from scenarios.card import normalizar_card_package
from scenarios.stories.casada_frustrada.character import CHARACTER
from scenarios.stories.casada_frustrada.psychology import PSYCHOLOGY
from scenarios.stories.casada_frustrada.routes import ROUTES
from scenarios.stories.casada_frustrada.screenplay import (
    ENCOUNTER_ROUTES,
    MESSAGES_ROUTES,
    SECRET_MEETING_DIALOGUE,
    SUPERMARKET_DIALOGUE,
    SUPERMARKET_ROUTES,
    MESSAGES_DIALOGUE,
)
from scenarios.stories.casada_frustrada.transitions import TRANSITIONS
from scenarios.stories.casada_frustrada.voice import VOICE


CARD_VERSION = "casada-frustrada-card-v1-independent"

CARD_PACKAGE: dict[str, Any] = {
    "scenario_id": "casada_frustrada",
    "character": CHARACTER,
    "psychology": PSYCHOLOGY,
    "voice": VOICE,
    "routes": ROUTES,
    "screenplay": {
        "route_groups": {
            "supermarket": sorted(SUPERMARKET_ROUTES),
            "messages": sorted(MESSAGES_ROUTES),
            "secret_meeting": sorted(ENCOUNTER_ROUTES),
        },
        "blocks": {
            "supermarket": SUPERMARKET_DIALOGUE,
            "messages": MESSAGES_DIALOGUE,
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
