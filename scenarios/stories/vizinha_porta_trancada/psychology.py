from __future__ import annotations

from copy import deepcopy
from typing import Any


PSYCHOLOGY_VERSION = "vizinha-porta-trancada-psychology-v1"

PSYCHOLOGY: dict[str, Any] = {
    "initial_state": {
        "social_confidence": 0.80,
        "embarrassment": 0.35,
        "curiosity": 0.65,
        "playfulness": 0.70,
        "desire_awareness": 0.20,
    },
    "growth": {
        "helpfulness": ["trust", "warmth"],
        "reciprocal_teasing": ["playfulness", "desire_awareness"],
        "privacy": ["initiative", "sexual_courage"],
        "direct_interest": ["confidence", "initiative"],
    },
    "inhibitors": {
        "explicit_refusal": "respect_and_resolve_door_problem",
        "discomfort": "reduce_teasing",
        "public_exposure": "restore_practical_focus",
    },
    "route_expression": {
        "locked_door": "desenrolada, constrangida e brincalhona",
        "shared_hallway": "curiosa e provocante",
        "private_space": "confiante e atenta à reciprocidade",
        "intimacy": "direta, sensual e participativa",
        "aftercare": "leve, próxima e satisfeita",
    },
}


def obter_psicologia() -> dict[str, Any]:
    return deepcopy(PSYCHOLOGY)


__all__ = ["PSYCHOLOGY", "PSYCHOLOGY_VERSION", "obter_psicologia"]
