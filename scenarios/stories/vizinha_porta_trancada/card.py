from __future__ import annotations

from copy import deepcopy
from typing import Any

from scenarios.card import normalizar_card_package
from scenarios.stories.vizinha_porta_trancada.character import CHARACTER
from scenarios.stories.vizinha_porta_trancada.psychology import PSYCHOLOGY
from scenarios.stories.vizinha_porta_trancada.routes import ROUTES
from scenarios.stories.vizinha_porta_trancada.screenplay import SCREENPLAY
from scenarios.stories.vizinha_porta_trancada.transitions import TRANSITIONS
from scenarios.stories.vizinha_porta_trancada.voice import VOICE


CARD_VERSION = "vizinha-porta-trancada-card-v1-independent"

CARD_PACKAGE: dict[str, Any] = {
    "scenario_id": "vizinha_porta_trancada",
    "character": CHARACTER,
    "psychology": PSYCHOLOGY,
    "voice": VOICE,
    "routes": ROUTES,
    "screenplay": SCREENPLAY,
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
        "screenplay_is_local_to_card": True,
        "global_voice_must_not_override_card": True,
        "director_must_recommend_route_semantically": True,
    },
}


def obter_card() -> dict[str, Any]:
    return normalizar_card_package(deepcopy(CARD_PACKAGE))


__all__ = ["CARD_PACKAGE", "CARD_VERSION", "obter_card"]
